import scrapy
import time
import re


class AlkoSpider(scrapy.Spider):
    name = "alko"
    allowed_domains = ["alkoteka.com"]
    start_urls = ["https://alkoteka.com/catalog/slaboalkogolnye-napitki-2", 
                  "https://alkoteka.com/catalog/krepkiy-alkogol",
                  "https://alkoteka.com/catalog/vino"]

    city_uuid = "4a70f9e0-46ae-11e7-83ff-00155d026416"


    def start_requests(self):
        api_url = self.build_categories()

        for i in api_url:  
            yield scrapy.Request(i, callback=self.parse_category)


    def build_categories(self):
        cat_names = [url.rstrip('/').split('/')[-1] for url in self.start_urls]
        xhr_urls = [f'https://alkoteka.com/web-api/v1/product?city_uuid={self.city_uuid}&page=1&per_page=10&root_category_slug={name}' for name in cat_names]
        return xhr_urls


    def parse_category(self, response):
        if response.json().get("meta").get("total") > 99:
            items = response.json().get("results", [])

            for i in items:
                product_url = i.get("product_url")
                product_url_last = product_url.rstrip('/').split('/')[-1]

                product_api_url = f"https://alkoteka.com/web-api/v1/product/{product_url_last}?city_uuid={self.city_uuid}"
                yield scrapy.Request(product_api_url, callback=self.parse, meta={"product_url": product_url,
                                                                                 "action_labels": i.get("action_labels")})
        else:
            return



    def parse(self, response):
        data = response.json().get("results", [])
        
        yield {
            "timestamp": int(time.time()),  # Дата и время сбора товара в формате timestamp.
            "RPC" : data.get("uuid"),  # Уникальный код товара.
            "url": response.meta.get("product_url"),  # Ссылка на страницу товара.
            "title": f'{data.get("name")}, {next(block.get("max") for block in data.get("description_blocks") if block.get("code") == "obem")}', # Заголовок/название товара (! Если в карточке товара указан цвет или объем, но их нет в названии, необходимо добавить их в title в формате: "{Название}, {Цвет или Объем}").
            "marketing_tags": [i.get("title") for i in response.meta.get("action_labels")],  # Список маркетинговых тэгов, например: ['Популярный', 'Акция', 'Подарок']. Если тэг представлен в виде изображения собирать его не нужно.
            "brand": next((block.get("values", [{}])[0].get("name") for block in data.get("description_blocks") if block.get("code") == "brend"), "Неизвестно"),  # Бренд товара.
            "section": [data.get("category").get("parent").get("name"), data.get("category").get("name")],  # Иерархия разделов, например: ['Игрушки', 'Развивающие и интерактивные игрушки', 'Интерактивные игрушки'].
            "price_data": {
                "current": float(data.get("price")),  # Цена со скидкой, если скидки нет то = original.
                "original": float(data.get("prev_price")),  # Оригинальная цена.
                "sale_tag": f"Скидка {0 if float(data.get('price_details')[0].get('price')) == float(data.get('price_details')[0].get('prev_price')) else round((1 - float(data.get('price_details')[0].get('price')) / float(data.get('price_details')[0].get('prev_price'))) * 100)}%"  # Если есть скидка на товар то необходимо вычислить процент скидки и записать формате: "Скидка {discount_percentage}%".
            },
            "stock": {
                "in_stock": data.get("available"),  # Есть товар в наличии в магазине или нет.
                "count": data.get("quantity_total")  # Если есть возможность получить информацию о количестве оставшегося товара в наличии, иначе 0.
            },
            "assets": {
                "main_image": data.get("image_url"),  # Ссылка на основное изображение товара.
                "set_images": [data.get("image_url")],  # Список ссылок на все изображения товара.
                "view360": ["No 360"],  # Список ссылок на изображения в формате 360.
                "video": ["No video"]  # Список ссылок на видео/видеообложки товара.
            },
            "metadata": {
            "__description": next((block.get("content") for block in data.get("text_blocks") if block.get("title") == "Описание"), "Отсутствует"),  # Описание товара
            "production_features": next((block.get("content") for block in data.get("text_blocks") if block.get("title") == "Особенности производства"), "Отсутствует"),
            "vendor_code": data.get("vendor_code"),
            "country_name": data.get("country_name"),
            "max_obem": next(block.get("max") for block in data.get("description_blocks") if block.get("code") == "obem"),
            "max_krepost": next(block.get("max") for block in data.get("description_blocks") if block.get("code") == "krepost"),
            "min_obem": next(block.get("min") for block in data.get("description_blocks") if block.get("code") == "obem"),
            "min_krepost": next(block.get("min") for block in data.get("description_blocks") if block.get("code") == "krepost")
            },
            "variants": 1,


        }
