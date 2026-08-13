import json
import os
import time
import pandas as pd
import requests

from datetime import datetime
from typing import List, Dict, Any, Hashable, Optional
from pandas import DataFrame
from concurrent.futures import ThreadPoolExecutor
from src.config import CACHE_FILE_CBR, CACHE_FILE_FINNHUB
from src.utils import load_transactions, _save_cache, _load_cache, get_user_setting

# Кэш: храним весь ответ ЦБ целиком + время запроса
_cbr_cache: Dict[str, Any] = {}


def data_for_view_page(df: DataFrame, datetime_str):
    """
    Формирует словарь данных для отображения на странице приветствия.

    Собирает:
      - приветствие по времени суток;
      - статистику по картам (расходы и кэшбэк);
      - топ самых дорогих транзакций;
      - курсы валют (с кэшем ЦБ);
      - котировки акций (с кэшем Finnhub).

    :param df: DataFrame с транзакциями.
    :param datetime_str: Строка даты в формате "YYYY-MM-DD HH:MM:SS".
    :return: Словарь с данными для фронтенда/шаблона.
    """
    # Получение ДатаФрейма транзакций с начала месяца до даты, указанной пользователем
    transactions_by_range = get_transactions_by_date_range_df(df, datetime_str)

    cards_data = group_transactions_by_cards(transactions_by_range)
    top_transactions = get_top_n_expensive_transactions(transactions_by_range)

    return {
        "greeting": get_greeting(datetime_str),
        "cards": cards_data,
        "top_transactions": top_transactions,
        "currency_rates": get_currency_rates(),
        "stock_prices": get_stock_prices(),
    }


def get_greeting(datetime_str: str) -> str:
    """
    Возвращает приветствие в зависимости от часа суток.

    Если строка даты некорректна, возвращает нейтральное приветствие.

    :param datetime_str: Дата и время в формате "YYYY-MM-DD HH:MM:SS".
    :return: Строка с приветствием.
    """
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "Доброго времени суток!"

    hour = dt.hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def get_transactions_by_date_range_df(df: DataFrame, date_str: str) -> pd.DataFrame:
    """
    Фильтрует DataFrame: оставляет транзакции с начала месяца по указанную дату.

    Начало месяца — 00:00:00 первого числа месяца указанной даты.
    Конец диапазона — указанная дата.

    :param df: Исходный DataFrame с колонкой "date".
    :param date_str: Конечная дата в формате "YYYY-MM-DD HH:MM:SS".
    :return: Отфильтрованный DataFrame.
    """
    end_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mask = (df["date"] >= start_date) & (df["date"] <= end_date)

    return df.loc[mask]


def get_top_n_expensive_transactions(df: pd.DataFrame, top_n: int = 5) -> list[dict[Hashable, Any]]:
    """
    Возвращает список топ-N самых дорогих транзакций по модулю суммы.

    Для каждой транзакции:
      - форматирует дату в строку "DD.MM.YYYY";
      - извлекает цифры из маски номера карты (если колонка есть);
      - оставляет только нужные колонки.

    :param df: DataFrame транзакций.
    :param top_n: Количество топ-транзакций.
    :return: Список словарей с данными транзакций.
    """

    # 1. Делаем копию, чтобы не менять оригинал
    work_df = df.copy()

    # 2. Сортируем по модулю суммы (amount) , по убыванию
    sorted_df = work_df.sort_values(
        by="amount",
        key=abs,
        ascending=False
    )

    # 3. Берем топ-N строк
    top_transactions = sorted_df.head(top_n).copy()

    # 4. Оставляем ТОЛЬКО нужные колонки
    available_columns = [
        col
        for col in ["date", "amount", "category", "description"]
        if col in top_transactions.columns
    ]
    top_transactions = top_transactions[available_columns]

    # вытягиваем только цифры из номера-маски карты, по типу *5051 → 5051
    if "mask_card_number" in top_transactions.columns:
        top_transactions["mask_card_number"] = (
            top_transactions["mask_card_number"]
            .astype(str)
            .str.extract(r'(\d+)')  # берёт первую последовательность цифр
        )

    # Форматируем дату: из datetime → строка "21.12.2021"
    if "date" in top_transactions.columns:
        # Защита: если вдруг там не дата, а строка - то ничего не ломаемся
        if not pd.api.types.is_datetime64_any_dtype(top_transactions["date"]):
            top_transactions["date"] = pd.to_datetime(
                top_transactions["date"],
                dayfirst=True,
                errors="coerce"
            )

        top_transactions["date"] = top_transactions["date"].dt.strftime("%d.%m.%Y")

    return top_transactions.to_dict(orient="records")


def group_transactions_by_cards(df: DataFrame):
    """
    Группирует транзакции по последним 4 цифрам карты, считает расходы и кэшбэк.

    Оставляются только строки с заполненным card_last_4 и отрицательной суммой (расходы).
    Суммы расходов приводятся к положительному значению (модуль).

    :param df: DataFrame транзакций с колонками card_last_4, amount, cashback.
    :return: Список словарей: [{"last_digits": "...", "total_spend": ..., "cashback": ...}, ...]
    """
    # Оставляем только строки, где есть номер карты
    df_clean = df.dropna(subset=["card_last_4"]).copy()

    if df_clean.empty:
        return []

    # 1. Фильтруем только расходы: оставляем строки, где payment_amount < 0
    expenses_df = df_clean[df_clean["amount"] < 0].copy()

    if expenses_df.empty: return []

    # 2. Группируем по чистым последним 4 цифрам
    grouped = expenses_df.groupby("card_last_4", dropna=False)

    # 3. Агрегируем: считаем сумму расходов и кэшбэка
    agg_df = grouped.agg(
        total_spend=("amount", "sum"),
        cashback=("cashback", "sum")
    ).reset_index()

    # 4. Убираем минус у расходов: делаем модуль (абсолютное значение)
    agg_df["total_spend"] = agg_df['total_spend'].abs().round(2)

    # 5. Переименовываем колонку для JSON-ответа
    agg_df = agg_df.rename(columns={"card_last_4": "last_digits"})

    return agg_df.to_dict(orient="records")


def get_currency_rates() -> List[Dict[str, Any]]:
    """
    Получает курсы валют для списка user_currencies из настроек.

    Использует дисковый кэш: если данные свежие (меньше CACHE_TTL), запрос к ЦБ не делается.
    При отсутствии/устаревшем кэше выполняется один запрос к API ЦБ и результат сохраняется.

    :return: Список словарей вида: [{"currency": "USD", "rate": 90.5, "from_cache": True}, ...]
    """
    # Валидация и получение значения поля "user_currencies" из файла настроек "user_settings.json"
    user_currencies = get_user_setting("user_currencies")

    # Проверка поля user_currencies в файле настроек "user_settings.json"
    if not isinstance(user_currencies, list):
        raise ValueError("Ошибка! В файле <user_settings.json> поле user_currencies должно быть списком")

    # 1. Пытаемся загрузить кэш с диска
    cbr_data = _load_cache(CACHE_FILE_CBR)
    from_cache = False

    # 2. Если нет свежих данных — делаем ровно ОДИН запрос к ЦБ
    if cbr_data is None:
        try:
            response = requests.request("get", "https://www.cbr-xml-daily.ru/daily_json.js", timeout=5.0)
            response.raise_for_status()
            cbr_data = response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError("упс!!! Превышено время ожидания ответа от API сервиса")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"упс!!! Ошибка сети при запросе курсов валют: {e}")
        except ValueError as e:
            raise RuntimeError(f"Не удалось распарсить ответ API от ЦБ: {e}") from e

        # Сохраняем весь ответ в кэш вместе с временем
        _save_cache(file_path=CACHE_FILE_CBR, data={"data": cbr_data, "timestamp": time.time()})
    else:
        from_cache = True

    cbr_currencies = cbr_data.get("Valute", {})

    current_courses = []
    for currency in user_currencies:
        if currency in cbr_currencies:
            current_courses.append({
                "currency": currency,
                "rate": cbr_currencies[currency]["Value"],

                # упрощённо: если брали из кэша, то from_cache=True
                "from_cache": from_cache
            })
        else:
            pass

    return current_courses


def get_stock_prices():
    """
    Получает котировки акций для списка user_stocks из настроек.

    Использует дисковый кэш по времени. Если кэш устарел или отсутствует,
    параллельно запрашивает котировки для всех тикеров (до 5 потоков).
    Один упавший тикер не ломает весь результат.

    :return: Список словарей вида: [{"stock": "AAPL", "price": 192.5, "from_cache": True}, ...]
    """
    url_finnhub = "https://finnhub.io/api/v1/quote"
    token = os.getenv("API_KEY_FINNHUB")

    if not token:
        raise RuntimeError("API ключ API_KEY_FINNHUB не найден в переменных окружения")

    # Валидация и получение значения поля "user_stocks" из файла настроек "user_settings.json"
    user_stocks = get_user_setting("user_stocks")

    # Проверка поля user_stocks в файле настроек "user_settings.json"
    if not isinstance(user_stocks, list):
        raise ValueError("Ошибка! В файле <user_settings.json> поле user_stocks должно быть списком")

    # 1. Пробуем загрузить кэш
    finn_data = _load_cache(CACHE_FILE_FINNHUB)
    from_cache = False
    raw_data: Optional[Dict[str, float]] = None

    if finn_data is not None:
        raw_data = finn_data.get("data")
        from_cache = True

    # 2. Если кэша нет или он битый — делаем запросы
    if raw_data is None:
        def fetch_quote(symbol):
            try:
                response = requests.get(
                    url_finnhub,
                    params={"symbol": symbol, "token": token},
                    timeout=5.0,
                )
                response.raise_for_status()
                return symbol, response.json().get("c")
            except Exception:
                # Если один тикер падает — остальные всё равно должны работать
                return symbol, None

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(fetch_quote, user_stocks))

        raw_data = {sym: price for sym, price in results if price is not None}

        # stock_prices = [{"stock": k, "price": v, "from_cache": from_cache} for k, v in response.items()]
        _save_cache(file_path=CACHE_FILE_FINNHUB, data={"data": raw_data, "timestamp": time.time()})

    # 3. Формируем итоговый список
    stock_prices: List[Dict[str, Any]] = [
        {"stock": sym, "price": price, "from_cache": from_cache}
        for sym, price in raw_data.items()
    ]

    return stock_prices


if __name__ == "__main__":
    # print(get_greeting("2021-12-25 15:01:01"))
    print(json.dumps(data_for_view_page(load_transactions(), "2021-12-31 15:01:01"), indent=2, ensure_ascii=False))
    # group_transactions_by_cards(load_transactions())
