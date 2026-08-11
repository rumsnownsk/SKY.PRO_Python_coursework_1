from pathlib import Path
from src.config import PROJECT_ROOT
from typing import List, Dict, Any
from datetime import datetime

import pandas as pd


def load_transactions(
        filename: str = "operations.xlsx",
        base_dir: Path | None = None
) -> pd.DataFrame:
    """Загружает транзакции из Excel и возвращает DataFrame с нормализованными типами."""

    # определяем путь головной директории проекта
    root_dir = base_dir if base_dir else PROJECT_ROOT
    file_path = root_dir / "data" / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: <{file_path}>")

    if file_path.stat().st_size == 0:
        raise ValueError(f"Файл <{file_path}> пустой")

    df = pd.read_excel(file_path)
    # ВАЖНО: делаем копию, чтобы не менять оригинал и избежать SettingWithCopyWarning
    df = df.copy()

    # Убираем лишние пробелы в названиях колонок
    df.columns = [col.strip().lower() for col in df.columns]

    COL_MAP = {
        "Дата операции": "date",
        "Дата платежа": "payment_date",
        "Номер карты": "mask_card_number",
        "Статус": "status",
        "Сумма операции": "amount",
        "Валюта операции": "currency",
        "Сумма платежа": "payment_amount",
        "Валюта платежа": "payment_currency",
        "Кэшбэк": "cashback",
        "Категория": "category",
        "MCC": "mcc",
        "Описание": "description",
        "Бонусы (включая кэшбэк)": "bonuses",
        "Округление на инвесткопилку": "rounding_to_invest",
        "Сумма операции с округлением": "amount_rounded",
    }

    col_map_normalized = {k.strip().lower(): v for k, v in COL_MAP.items()}

    df = df.rename(columns=col_map_normalized)

    df["card_last_4"] = (
        df["mask_card_number"]
        .astype(str)
        .str.extract(r'(\d{4})$')  # Берёт ровно 4 цифры в конце строки
    )

    # Приводим колонку "Дата операции" к datetime с правильным порядком день/месяц
    df["date"] = pd.to_datetime(
        df["date"],
        dayfirst=True,
        errors="coerce"
    )

    # Приводим суммы к float (нормализуем запятые в точки)
    amount_cols = ["amount", "payment_amount", "cashback", "bonuses", "amount_rounded"]
    for col in amount_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace("", "0")
                .astype(float)
            )

    return df


def format_transactions_for_response(
    transactions: List[Dict[str, Any]],
    date_format: str = "%d.%m.%Y"
) -> List[Dict[str, Any]]:
    """
    Преобразует поле 'operation_date' из datetime в строку заданного формата.
    Также округляет суммы до 2 знаков (для красивого вывода).

    :param transactions: список словарей (результат to_dict(orient='records'))
    :param date_format: формат даты для strftime, по умолчанию "%d.%m.%Y" -> "21.12.2021"
    :return: новый список словарей с отформатированными данными
    """
    formatted = []

    for t in transactions:
        # Создаём копию, чтобы не менять исходные данные
        row = t.copy()

        # Форматируем дату, если она есть и это datetime
        if "operation_date" in row and isinstance(row["operation_date"], datetime):
            row["date"] = row["operation_date"].strftime(date_format)
            # Удаляем исходное поле с datetime, если в ответе оно не нужно
            del row["operation_date"]
        elif "operation_date" in row:
            # Если вдруг там уже строка — оставляем как есть
            row["date"] = str(row["operation_date"])
            del row["operation_date"]

        # Округляем суммы до 2 знаков для красивого вывода (опционально)
        if "amount" in row and isinstance(row["amount"], (int, float)):
            row["amount"] = round(float(row["amount"]), 2)

        formatted.append(row)

    return formatted