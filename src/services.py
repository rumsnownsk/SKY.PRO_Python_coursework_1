import json
import re
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import numpy as np

from pandas import DataFrame

from src.utils import load_transactions

def best_cashback_from_category(df: DataFrame,year:int, month: int) -> Dict:
    """
    Возвращает словарь {категория: суммарный кэшбэк (целое число)} за месяц и год.

    Кэшбэк округляется до целого числа и сортируется по убыванию суммы.
    Пустые категории исключаются.
    """
    last_date = df["date"].max()
    first_date = df["date"].min()

    if not isinstance(month, int) or not isinstance(year, int):
        raise TypeError(f"month и year должны быть целыми числами. Последняя дата в транзакциях:{last_date.month}.{last_date.year}")
    if month < 1 or month > 12:
        raise ValueError("month должен быть от 1 до 12 (включительно)")
    if year < first_date.year or year > last_date.year:
        raise TypeError(f"Допустимый диапазон дат: начало - {first_date.month}.{first_date.year}; Конец - {last_date.month}.{last_date.year}")

    # 1. Фильтруем ДатаФрейм по конкретному месяцу конкретного года
    filtered = df[(df["date"].dt.year == year) & (df["date"].dt.month == month)].copy()
    if filtered.empty:
        return []

    filtered["cashback"] = pd.to_numeric(filtered["cashback"], errors="coerce")
    positive = filtered[(filtered["cashback"] > 0) & filtered["cashback"].notna()].copy()

    # Группируем, суммируем, округляем, приводим к int — и сразу to_dict
    result = (
        positive.groupby("category", dropna=True)["cashback"]
        .sum()
        .round()
        .astype(int)
        .sort_values(ascending=False)  # сортировка по сумме кэшбэка
    )

    return result.to_dict()

def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Считает сумму, которая попала бы в Инвесткопилку за указанный месяц.
    
    Параметры:
        month: строка в формате 'YYYY-MM' (например, '2024-11')
        transactions: список словарей с ключами 'date' (str 'YYYY-MM-DD') и 'amount' (float/int)
        limit: шаг округления (10, 50, 100)
    
    Возвращает:
        float: суммарный вклад в копилку за указанный месяц.
    """

    target_month, target_year = map(int, month.split("-"))

    total_saved = 0.0

    for t in transactions:
        tx_date = datetime.strptime(t["date"], "%Y-%m-%d")
        if tx_date.month != target_month & tx_date.year != target_month:
            continue
        amount = float(t["amount"])

        if amount % limit == 0:
            rounded = amount
        else:
            rounded = ((amount // limit + 1) * limit)
        saved = rounded - amount

        total_saved += saved

    return total_saved


def get_transactions_with_phone(df_tr: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Функция возвращает JSON со всеми транзакциями, содержащими в описании мобильные номера.
    :param df_tr:
    :return:
    """
    pattern = r"\+7 \d{3} \d{2,3}-\d{2}-\d{2}"

    mask = df_tr["description"].str.contains(pattern, regex=True, na=False)
    with_phone = df_tr[mask].copy()

    if with_phone.empty:
        return []

    # Обработка дат (если колонка есть)
    if "date" in with_phone.columns:
        # Сначала убедимся, что колонка datetime, потом конвертируем в строку
        if not pd.api.types.is_datetime64_any_dtype(with_phone["date"]):
            with_phone["date"] = pd.to_datetime(with_phone["date"], errors="coerce")
        with_phone["date"] = with_phone["date"].dt.strftime("%Y-%m-%d")

    with_phone = with_phone.replace({np.nan: None})

    return with_phone.to_dict(orient="records")

def get_transfer(df_tr:pd.DataFrame) -> List[Dict[str, Any]]:
    pattern = r"\w+\s+[А-ЯЁ]\."

    with_transfer = df_tr[
        df_tr["category"].str.contains("Переводы", regex=True, na=False)
        &
        df_tr["description"].str.contains(pattern, regex=True, na=False)
    ].copy()

    if "date" in with_transfer.columns:
        # Сначала убедимся, что колонка datetime, потом конвертируем в строку
        if not pd.api.types.is_datetime64_any_dtype(with_transfer["date"]):
            with_transfer["date"] = pd.to_datetime(with_transfer["date"], errors="coerce")
        with_transfer["date"] = with_transfer["date"].dt.strftime("%Y-%m-%d")

    with_transfer = with_transfer.replace({np.nan: None})


    return with_transfer.to_dict(orient="records")
