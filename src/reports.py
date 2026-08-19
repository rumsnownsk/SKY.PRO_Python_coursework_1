import json
import os
from calendar import month
from functools import wraps
from typing import Optional, Callable, Any

import pandas as pd

DEFAULT_REPORT_FILENAME = "report_spending.json"

def save_report(filename: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Сначала запускаем саму функцию и получаем результат (DataFrame)
            result = func(*args, **kwargs)

            if not isinstance(result, pd.DataFrame):
                return result

            # 2. Выбираем имя файла
            target_filename = filename if filename else DEFAULT_REPORT_FILENAME

            # 3. Готовим данные, чтобы json.dump не упал на датах и NaN
            data_to_save = _prepare_for_json(result)

            # 4. сохраняем в папку
            os.makedirs('tmp', exist_ok=True)
            full_path = os.path.join("tmp", target_filename)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, ensure_ascii=False)
            except Exception as e:
                pass

            return result
        return wrapper
    return decorator


def _prepare_for_json(data: Any) -> Any:
    """
    Вспомогательная функция: превращает DataFrame в список словарей,
    чистит даты и NaN, чтобы они стали валидным JSON.
    """
    records = data.to_dict(orient="records")
    cleaned = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, pd.Timestamp):
                clean_row[k] = v.strftime("%Y-%m-%d") if pd.notna(v) else None
            # Если это NaN (пустое число) -> превращаем в None (который станет null в JSON)
            elif isinstance(v, float) and pd.isna(v):
                clean_row[k] = None
            else:
                clean_row[k] = v
        cleaned.append(clean_row)
    return cleaned



@save_report("report_spending_by_category.json")
def spending_by_category(transactions: pd.DataFrame,
                         category: str,
                         date: Optional[str] = None) -> pd.DataFrame:
    if transactions.empty:
        return pd.DataFrame()

    # устанавливаем даты начала и конца периода
    if date is None:
        ref_date = pd.Timestamp.today()
    else:
        try:
            ref_date = pd.to_datetime(date)
        except ValueError:
            ref_date = pd.Timestamp.today()

    start_date = ref_date - pd.DateOffset(months=3)

    # фильтруем данные по периоду и категории
    mask_date = (transactions["date"] >= start_date) & (transactions["date"] <= ref_date)
    mask_category = transactions["category"].str.contains(category, case=False, na=False)

    # получаем новый датафрейм
    res_df = transactions[mask_date & mask_category].copy()

    if not res_df.empty:
        res_df = res_df.sort_values(by="date", ascending=False)

    return res_df

@save_report("report_spending_by_weekday.json")
def spending_by_weekday(transactions: pd.DataFrame,
                        date: Optional[str] = None) -> pd.DataFrame:
    if transactions.empty:
        return pd.DataFrame(columns=["weekday", "avg_amount"])

    if date is None:
        ref_date = pd.Timestamp.today()
    else:
        try:
            ref_date = pd.to_datetime(date)
        except (ValueError, TypeError):
            ref_date = pd.Timestamp.today()
    start_date = ref_date - pd.DateOffset(months=3)

    df = transactions.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Убираем строки, где дата не распарсилась (NaN)
    df = df.dropna(subset=["date"])

    mask = (df["date"] >= start_date) & (df["date"] <= ref_date)
    filtered = df[mask].copy()

    if filtered.empty:
        return pd.DataFrame(columns=["weekday", "avg_amount"])

    day_map = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье"
    }
    filtered["weekday"] = filtered["date"].dt.dayofweek.map(day_map)

    result = (
        filtered.groupby("weekday", sort=False)["amount"]
        .mean()
        .reset_index()
        .rename(columns={"amount": "avg_amount"})
    )
    return result

