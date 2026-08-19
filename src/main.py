import json

from dotenv import load_dotenv

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
    # print(investment_bank("2024-11", ))

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
    print(
        json.dumps(
            get_transfer(df_transactions),
            indent=2,
            ensure_ascii=False
        ))
