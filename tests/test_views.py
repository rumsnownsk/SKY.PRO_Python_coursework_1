import pandas as pd
import pytest

from src.views import *

@pytest.fixture
def operations_df():
    operations_df = pd.DataFrame([
        {"date": "2020-11-01 10:00:00", "amount": -100, "category": "Еда", "card_last_4": "4444", "cashback": 50.0},
        {"date": "2020-11-10 12:30:00", "amount": -505, "category": "Транспорт", "card_last_4": "4444", "cashback": 0},
        {"date": "2020-11-20 09:15:00", "amount": 2000, "category": "Зарплата", "card_last_4": "8888", "cashback": 0},
        {"date": "2020-11-25 18:45:00", "amount": -300, "category": "Одежда", "card_last_4": "8888", "cashback": 10.0},
        {"date": "2020-11-30 20:01:01", "amount": -750, "category": "Кафе", "card_last_4": "4444", "cashback": 0.0},
        {"date": "2020-12-05 11:00:00", "amount": -200, "category": "Такси", "card_last_4": "2222", "cashback": 50.0},

        # Новый кейс: такая же сумма, как у одной из существующих, чтобы проверить стабильность сортировки
        {"date": "2020-12-10 14:20:00", "amount": -300, "category": "Электроника", "card_last_4": "1111",
         "cashback": 25.0},

        # Новый кейс: нулевая транзакция (не должна попадать в топ дорогих трат, если считать только расходы)
        {"date": "2020-12-15 09:00:00", "amount": 0, "category": "Прочее", "card_last_4": "9999", "cashback": 0.0},

        # Новый кейс: ещё одна крупная трата, чтобы топ-3 был не только из одной карты
        {"date": "2020-12-20 18:00:00", "amount": -400, "category": "Отдых", "card_last_4": "7777", "cashback": 15.0},
    ])

    # Важно: сразу приводим колонку date к типу datetime, как это делает функция внутри
    operations_df["date"] = pd.to_datetime(operations_df["date"], format="%Y-%m-%d %H:%M:%S")
    return operations_df


def test_get_greeting():
    morning_time = "2020-11-30 10:01:01"
    evening_time = "2020-11-30 20:01:01"
    error_time = "2020.11.30 10.01.01"
    assert get_greeting(morning_time) == "Доброе утро"
    assert get_greeting(evening_time) == "Добрый вечер"
    assert get_greeting(error_time) == "Доброго времени суток!"

def test_get_transactions_month_to_date_df(operations_df:pd.DataFrame):
    end_date_str = "2020-11-30 20:01:01"

    result = get_transactions_month_to_date_df(operations_df, end_date_str)

    assert len(result) == 5
    assert isinstance(result, pd.DataFrame)
    assert result["date"].max() == pd.to_datetime(end_date_str)
    assert result["date"].min() == pd.to_datetime("2020-11-01 10:00:00")

def test_get_transactions_by_date_range_df(operations_df:pd.DataFrame):
    end_date_str = "2020-11-30 20:01:01"

    result = get_transactions_by_date_range_df(operations_df, end_date_str, 'm')

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 5
    assert result["date"].max() == pd.to_datetime(end_date_str)
    assert (result["date"].dt.month == 11).all

def test_group_transactions_by_cards(operations_df: pd.DataFrame):
    result = group_transactions_by_cards(operations_df)

    assert isinstance(result, list)
    assert all(isinstance(row, dict) for row in result)
    assert len(result) == 5

    # Проверяем что вернулись только нужные ключи
    for row in result:
        assert set(row.keys()) == {"last_digits", "total_spend", "cashback"}

    card_4444 = next((row for row in result if row["last_digits"] == "4444"), None)
    assert card_4444 is not None
    assert card_4444["total_spend"] == 1355.0
    assert card_4444["cashback"] == 50.0

    # для карты 8888
    card_8888 = next((row for row in result if row["last_digits"] == "8888"), None)
    assert card_8888 is not None
    assert card_8888["total_spend"] == 300.0
    assert card_8888["cashback"] == 10.0

    # для карты 2222
    card_2222 = next((row for row in result if row["last_digits"] == "2222"), None)
    assert card_2222 is not None
    assert card_2222["total_spend"] == 200.0
    assert card_2222["cashback"] == 50.0

def test_get_top_n_expensive_transactions(operations_df: pd.DataFrame):
    result = get_top_n_expensive_transactions(operations_df, top_n=3)
    assert isinstance(result, list)
    assert len(result) == 3

    assert result[0]["amount"] == -750
    assert result[1]["amount"] == -505
    assert result[2]["amount"] == -400

    assert isinstance(result[0]["date"], str)
    assert result[0]["date"][2] == "." and result[0]["date"][5] == "."

def test_get_top_n_expensive_transactions_no_expenses(operations_df: pd.DataFrame):
    only_income = operations_df[operations_df["amount"] >= 0].copy()
    result = get_top_n_expensive_transactions(only_income)

    assert isinstance(result, list)
    assert len(result) == 0
