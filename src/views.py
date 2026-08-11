import json
from datetime import datetime
from typing import List, Dict, Any, Hashable
from zoneinfo import available_timezones

from pandas import DataFrame
from src.utils import load_transactions

import pandas as pd


def data_to_view_page(df: DataFrame, datetime_str):
    transactions_by_range = get_transactions_by_date_range_df(df, datetime_str)

    top_transactions = get_top_n_expensive_transactions(transactions_by_range)

    return {
        "greeting": get_greeting(datetime_str),
        # "cards": cards_df,
        "top_transactions": top_transactions
    }


def get_greeting(datetime_str: str) -> str:
    """
    Функция принимает строку формата YYYY-MM-DD HH:MM:SS и возвращает приветствие
    в зависимости от текущего времени суток
    :param datetime_str:
    :return:
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
    Возвращает транзакции с начала месяца по указанную дату.
    date_str: строка формата YYYY-MM-DD HH:MM:SS
    """
    end_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mask = (df["date"] >= start_date) & (df["date"] <= end_date)

    return df.loc[mask]


def get_top_n_expensive_transactions(df: pd.DataFrame, top_n: int = 5) -> list[dict[Hashable, Any]]:
    """
    Возвращает топ-N самых дорогих операций.
    Колонка 'date' уже есть в DataFrame (из load_transactions),
    здесь мы её форматируем в строку "%d.%m.%Y".
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

    if "card_number" in top_transactions.columns:
        top_transactions["card_number"] = (
            top_transactions["card_number"]
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


def default_serializer(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError(f"Type not serializable: {type(obj)}")


if __name__ == "__main__":
    # print(get_greeting("2021-12-25 15:01:01"))
    print(json.dumps(data_to_view_page(load_transactions(), "2021-12-31 15:01:01"), indent=2, ensure_ascii=False,
                     default=default_serializer))
    # print(data_to_view_page(load_transactions(), "2021-12-31 15:01:01"))
    # get_top_transactions_by_date_range()
