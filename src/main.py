import json

from dotenv import load_dotenv

from src.reports import *
from src.utils import load_transactions, datetime_handle
from src.views import page_events, page_main
from src.services import best_cashback_from_category, get_transactions_with_phone, get_transfer

if __name__ == "__main__":
    # загрузка библиотеки dotenv()
    load_dotenv()

    df_transactions = load_transactions()
    # ==================   Задача №1 "Веб-страницы"   ===============================
    """
    Страница «Главная».
    Этот код запускает функцию 'page_main' в модуле src/views.py,
    которая возвращает json-данные для страницы 'Главная'
    """
    # print(json.dumps(page_main("2021-12-31 15:01:01"), indent=2, ensure_ascii=False))

    """
    Страница «События».
    Этот код запускает функцию 'page_events' в модуле src/views.py,
    которая возвращает json-данные для страницы 'События'
    """
    # print(json.dumps(page_events("2020-11-30 15:01:01", "y"), indent=2, ensure_ascii=False))

    # =================   Задача №2 "Сервисы"   =============

    """    
    Этот код запускает функцию 'best_cashback_from_category' 
    в модуле src/services.py
    """
    # print(json.dumps(best_cashback_from_category(df_transactions, year=2021, month=11), indent=2, ensure_ascii=False))


    """    
    Этот код запускает функцию 'get_transactions_with_phone' 
    в модуле src/services.py
    """
    # print(
    #     json.dumps(
    #         get_transactions_with_phone(df_transactions),
    #         indent=2,
    #         ensure_ascii=False
    #     ))

    """    
    Этот код запускает функцию 'get_transfer' 
    в модуле src/services.py
    """
    # print(
    #     json.dumps(
    #         get_transfer(df_transactions),
    #         indent=2,
    #         ensure_ascii=False
    #     ))


    # =================   Задача №3 "Отчёты"   =============

    """    
    Этот код запускает функцию 'spending_by_category' 
    в модуле src/reports.py
    а прикрученный к ней декоратор сохраняет данные в файл 'report_spending_by_category.json'
    """
    # spending_by_category(df_transactions,"Каршеринг", "2021-12-30")

    """    
    Этот код запускает функцию 'spending_by_weekday' 
    в модуле src/reports.py
    а прикрученный к ней декоратор сохраняет данные в файл 'report_spending_by_weekday.json'
    """
    # res = spending_by_weekday(df_transactions, "2021-12-30")
    # json_str = res.to_json(orient="records", indent=2)
    # print("\nРезультат (JSON):")
    # print(json.dumps(json.loads(json_str), indent=2, ensure_ascii=False))
