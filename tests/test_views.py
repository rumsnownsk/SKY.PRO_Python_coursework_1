import json
from unittest.mock import patch

import pandas as pd
import pytest

from src.views import *


@pytest.fixture
def operations_df():
    operations_df = pd.DataFrame(
        [
            {
                "date": "2020-11-01 10:00:00",
                "amount": -100,
                "category": "Еда",
                "card_last_4": "4444",
                "cashback": 50.0,
            },
            {
                "date": "2020-11-10 12:30:00",
                "amount": -505,
                "category": "Транспорт",
                "card_last_4": "4444",
                "cashback": 0,
            },
            {
                "date": "2020-11-20 09:15:00",
                "amount": 2000,
                "category": "Зарплата",
                "card_last_4": "8888",
                "cashback": 0,
            },
            {
                "date": "2020-11-25 18:45:00",
                "amount": -300,
                "category": "Одежда",
                "card_last_4": "8888",
                "cashback": 10.0,
            },
            {
                "date": "2020-11-30 20:01:01",
                "amount": -750,
                "category": "Кафе",
                "card_last_4": "4444",
                "cashback": 0.0,
            },
            {
                "date": "2020-12-05 11:00:00",
                "amount": -200,
                "category": "Такси",
                "card_last_4": "2222",
                "cashback": 50.0,
            },
            {
                "date": "2020-12-10 14:20:00",
                "amount": -300,
                "category": "Электроника",
                "card_last_4": "1111",
                "cashback": 25.0,
            },
            {"date": "2020-12-15 09:00:00", "amount": 0, "category": "Прочее", "card_last_4": "9999", "cashback": 0.0},
            {
                "date": "2020-12-16 09:00:00",
                "amount": 10000,
                "category": "Пополнение",
                "card_last_4": "9999",
                "cashback": 0.0,
            },
            {
                "date": "2020-12-16 10:00:00",
                "amount": 10000,
                "category": "Пополнение",
                "card_last_4": "9999",
                "cashback": 0.0,
            },
            {
                "date": "2020-12-20 18:00:00",
                "amount": -400,
                "category": "Отдых",
                "card_last_4": "7777",
                "cashback": 15.0,
            },
        ]
    )

    # Важно: сразу приводим колонку date к типу datetime, как это делает функция внутри
    operations_df["date"] = pd.to_datetime(operations_df["date"], format="%Y-%m-%d %H:%M:%S")
    return operations_df


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError("Mocked error")


@patch("src.views._load_cache", return_value=None)  # нет кэша → должен пойти в сеть
@patch("requests.request")
@patch("src.views._save_cache")
def test_get_currency_rates_from_api(mock_save, mock_request, mock_load):
    mock_request.return_value = MockResponse(
        {
            "Valute": {
                "USD": {"Value": 75.5},
                "EUR": {"Value": 85.0},
            }
        }
    )

    rates = get_currency_rates()

    # Запрос к API был сделан
    mock_request.assert_called_once()
    # Кэш был сохранён
    mock_save.assert_called_once()

    assert len(rates) == 2
    assert any(r["currency"] == "USD" for r in rates)
    assert any(r["currency"] == "EUR" for r in rates)


@patch("src.views._load_cache")  # <-- Убрали return_value=None! Теперь это просто мок
@patch("requests.request")  # <-- Этот вызов вообще не должен произойти
@patch("src.views._save_cache")  # <-- И этот тоже
def test_get_currency_rates_from_cache(mock_save, mock_request, mock_load):
    # 1. Готовим данные, которые должны лежать в кэше
    cached_data = {
        "data": {
            "Valute": {
                "USD": {"Value": 76.0},
                "EUR": {"Value": 86.0},
            }
        },
        "timestamp": time.time(),
    }

    # 2. Говорим моку: когда вызовут _load_cache, верни вот эти данные
    mock_load.return_value = cached_data

    # 3. Вызываем функцию
    rates = get_currency_rates()

    # 4. Проверяем, что сеть НЕ трогали
    mock_request.assert_not_called()
    mock_save.assert_not_called()

    # 5. Проверяем результат
    assert len(rates) == 2
    assert any(r["currency"] == "USD" for r in rates)
    assert any(r["currency"] == "EUR" for r in rates)
    assert all(r["from_cache"] is True for r in rates)

    print("\nПолученные курсы из кэша:")
    print(json.dumps(rates, indent=2, ensure_ascii=False))


def test_get_greeting():
    morning_time = "2020-11-30 10:01:01"
    evening_time = "2020-11-30 20:01:01"
    error_time = "2020.11.30 10.01.01"
    assert get_greeting(morning_time) == "Доброе утро"
    assert get_greeting(evening_time) == "Добрый вечер"
    assert get_greeting(error_time) == "Доброго времени суток!"


def test_get_transactions_month_to_date_df(operations_df: pd.DataFrame):
    end_date_str = "2020-11-30 20:01:01"

    result = get_transactions_month_to_date_df(operations_df, end_date_str)

    assert len(result) == 5
    assert isinstance(result, pd.DataFrame)
    assert result["date"].max() == pd.to_datetime(end_date_str)
    assert result["date"].min() == pd.to_datetime("2020-11-01 10:00:00")


def test_get_transactions_by_date_range_df(operations_df: pd.DataFrame):
    date_str = "2020-11-30 20:01:01"

    result = get_transactions_by_date_range_df(operations_df, date_str, "m")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 5
    assert result["date"].max() == pd.to_datetime(date_str)
    assert (result["date"].dt.month == 11).all

    end_date_str = "2020-12-20 18:00:00"
    result_all = get_transactions_by_date_range_df(operations_df, end_date_str, "all")

    assert len(result_all) == len(operations_df)
    assert isinstance(result_all, pd.DataFrame)

    with pytest.raises(ValueError):
        assert get_transactions_by_date_range_df(operations_df, end_date_str, "e")


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


def test_get_expenses(operations_df: pd.DataFrame):
    result = get_expenses(operations_df)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"total_amount", "main", "transfer_and_cash"}

    # Проверяем типы
    assert isinstance(result["total_amount"], int)
    assert isinstance(result["main"], list)
    assert isinstance(result["transfer_and_cash"], list)

    # Сумма main + transfer_and_cash должна быть равна total_amount
    sum_main = sum(row["amount"] for row in result["main"])
    sum_transfers = sum(row["amount"] for row in result["transfer_and_cash"])
    assert sum_main + sum_transfers == result["total_amount"]


def test_get_expenses_empty_df():
    data = pd.DataFrame(columns=["amount"])
    result = get_expenses(data)

    assert result == {"total_amount": 0, "main": [], "transfer_and_cash": []}


def test_get_income(operations_df: pd.DataFrame):
    result = get_income(operations_df)

    assert set(result.keys()) == {"total_amount", "main"}
    assert isinstance(result["total_amount"], int)
    assert isinstance(result["main"], list)

    total_amount = int(result["total_amount"])
    sum_by_category = sum(item["amount"] for item in result["main"])
    assert total_amount == sum_by_category


def test_get_income_empty_df():
    df = pd.DataFrame(columns=["amount", "category"])
    result = get_income(df)
    assert result == {"total_amount": 0, "main": []}


@patch("os.getenv", return_value=None)
def test_get_stock_prices_no_api_key(mock_env):
    from src.views import get_stock_prices

    with pytest.raises(RuntimeError, match="API ключ API_KEY_FINNHUB не найден"):
        get_stock_prices()


@patch("src.views._load_cache", return_value=None)
@patch("os.getenv", return_value="fake_token")
@patch("requests.get")
def test_get_stock_prices_mixed_errors(mock_get, mock_env, mock_load):
    # Один тикер вернёт цену, другой — ошибку
    def side_effect(*args, **kwargs):
        symbol = kwargs.get("params", {}).get("symbol")
        if symbol == "AAPL":
            return MockResponse({"c": 190.5})
        else:
            # Для остальных тикеров эмулируем ошибку
            raise requests.exceptions.RequestException("Mocked network error")

    mock_get.side_effect = side_effect

    from src.views import get_stock_prices

    prices = get_stock_prices()

    # Должен вернуться хотя бы один успешный тикер
    assert len(prices) >= 1
    assert any(p["stock"] == "AAPL" and p["price"] == 190.5 for p in prices)


@patch("src.views.load_transactions")
@patch("src.views.get_transactions_month_to_date_df")
@patch("src.views.group_transactions_by_cards")
@patch("src.views.get_top_n_expensive_transactions")
@patch("src.views.get_greeting")
@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_page_main_structure(mock_stock, mock_currencies, mock_greeting, mock_top, mock_group, mock_range, mock_load):
    mock_load.return_value = pd.DataFrame()
    mock_range.return_value = pd.DataFrame()
    mock_group.return_value = []
    mock_top.return_value = []
    mock_greeting.return_value = "Доброе утро"
    mock_currencies.return_value = []
    mock_stock.return_value = []

    result = page_main("2020-11-30 10:00:00")

    assert isinstance(result, dict)
    assert set(result.keys()) == {"greeting", "cards", "top_transactions", "currency_rates", "stock_prices"}
    assert result["greeting"] == "Доброе утро"


@patch("src.views.load_transactions")
@patch("src.views.get_transactions_by_date_range_df")
@patch("src.views.get_expenses")
@patch("src.views.get_income")
@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_page_events_structure(mock_stock, mock_currencies, mock_income, mock_expenses, mock_range, mock_load):
    mock_load.return_value = pd.DataFrame()
    mock_range.return_value = pd.DataFrame()
    mock_expenses.return_value = {"total_amount": 0, "main": [], "transfer_and_cash": []}
    mock_income.return_value = {"total_amount": 0, "main": []}
    mock_currencies.return_value = []
    mock_stock.return_value = []

    result = page_events("2020-11-30 10:00:00", "m")

    assert isinstance(result, dict)
    assert set(result.keys()) == {"expenses", "income", "currency_rates", "stock_prices"}


def test_get_currency_rates_invalid_user_currencies():
    # Подменим get_user_setting, чтобы вернуть не список
    with patch("src.views.get_user_setting", return_value="not-a-list"):
        with pytest.raises(ValueError, match="должно быть списком"):
            get_currency_rates()


@patch("src.views._load_cache")
@patch("requests.request")
@patch("src.views._save_cache")
def test_get_currency_rates_cache_expired(mock_save, mock_request, mock_load):
    now = time.time()
    expired_cached_data = {
        "data": {
            "Valute": {
                "USD": {"Value": 70.0},
                "EUR": {"Value": 80.0},
            }
        },
        "timestamp": now - 86400 * 2,  # 2 дня назад — точно просрочено
    }
    mock_load.return_value = expired_cached_data

    mock_request.return_value = MockResponse(
        {
            "Valute": {
                "USD": {"Value": 75.5},
                "EUR": {"Value": 85.0},
            }
        }
    )

    rates = get_currency_rates()

    # Кэш устарел → запрос к API должен быть
    mock_request.assert_called_once()
    mock_save.assert_called_once()

    assert len(rates) == 2


@patch("src.views._load_cache", return_value=None)
@patch("requests.request", side_effect=requests.exceptions.Timeout)
@patch("src.views._save_cache")
def test_get_currency_rates_network_timeout(mock_save, mock_request, mock_load):
    with pytest.raises(RuntimeError, match="Превышено время ожидания"):
        get_currency_rates()
    mock_save.assert_not_called()


@pytest.mark.parametrize("range_type", ["w", "m", "y"])
def test_get_transactions_by_date_range_variants(operations_df, range_type):
    end_date_str = "2020-12-20 18:00:00"

    result = get_transactions_by_date_range_df(operations_df, end_date_str, range_type)

    assert isinstance(result, pd.DataFrame)

    # Подбираем ожидаемое количество строк уже после получения operations_df
    if range_type == "w":
        expected_count = 4  # пример: последние 7 дней
    elif range_type == "m":
        expected_count = 6  # ноябрьские транзакции
    elif range_type == "y":
        expected_count = len(operations_df)  # ✅ теперь operations_df — это реальный DataFrame

    assert len(result) == expected_count
