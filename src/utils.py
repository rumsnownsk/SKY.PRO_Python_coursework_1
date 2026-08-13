import json
import time
from pathlib import Path
from src.config import PROJECT_ROOT, CACHE_TTL
from typing import List, Dict, Any, Optional
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


def _load_cache(file_path) -> Optional[Dict[str, Any]]:
    if not file_path.exists():
        return None
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        timestamp = data.get("timestamp")
        if timestamp is None:
            return None
        age = time.time() - timestamp
        if age < CACHE_TTL:
            return data.get("data")
    except (json.JSONDecodeError, OSError, ValueError):
        # Файл битый или не JSON — считаем, что кэша нет
        pass
    return None


def _save_cache(file_path, data: Dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_setting(field):
    # определяем где лежит сам файл user_settings.json
    user_settings_file = PROJECT_ROOT / "src/user_settings.json"

    # Проверка файла настроек
    if not user_settings_file.exists():
        raise FileNotFoundError(f"⚠ Ошибка! Проверьте наличие файлика <{user_settings_file}>")
    if user_settings_file.stat().st_size == 0:
        raise ValueError(f"⚠ Ошибка! Файл настроек пуст: <{user_settings_file}>")

    # читаем файл настроек user_settings.json
    with open(user_settings_file, "r", encoding="utf-8") as f:
        user_settings = json.load(f)

    return user_settings.get(field, [])