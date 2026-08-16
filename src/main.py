import json

from dotenv import load_dotenv

from src.utils import load_transactions
from src.views import page_events, page_main

if __name__ == "__main__":
    # загрузка библиотеки dotenv()
    load_dotenv()

    json_transactions = load_transactions()

    # Страница «Главная».
    # Этот код запускает функцию 'page_main' в модуле views.py,
    # которая возвращает json-данные для страницы "Главная"
    print(json.dumps(page_main("2021-12-31 15:01:01"), indent=2, ensure_ascii=False))

    # Страница «События».
    # Этот код запускает функцию 'page_events' в модуле views.py,
    # которая возвращает json-данные для страницы "События"
    print(json.dumps(page_events("2020-11-30 15:01:01", "y"), indent=2, ensure_ascii=False))
