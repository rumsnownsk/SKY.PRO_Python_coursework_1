import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from pandas import Timestamp

from src.config import CACHE_TTL, PROJECT_ROOT


def load_transactions(filename: str = "operations.xlsx", base_dir: Path | None = None) -> pd.DataFrame:
    """
    Загружает транзакции из Excel-файла и возвращает DataFrame с нормализованными типами.

    Выполняет:
        - Проверку существования файла и его непустоты.
        - Переименование колонок по заранее заданному маппингу (с игнорированием регистра и пробелов).
        - Извлечение последних 4 цифр номера карты в отдельную колонку `card_last_4`.
        - Приведение колонки `date` к типу datetime (формат день/месяц/год).
        - Нормализацию денежных колонок: замена запятых на точки, приведение к float.

    Параметры
    ---------
    filename : str, default="operations.xlsx"
        Имя файла с транзакциями.
    base_dir : Path | None, default=None
        Корневая директория проекта. Если не указана, используется глобальная константа PROJECT_ROOT.

    Возвращает
    ----------
    DataFrame
        DataFrame с транзакциями и нормализованными данными.

    Исключения
    ----------
    FileNotFoundError
        Если указанный файл не существует.
    ValueError
        Если файл существует, но пустой.
    """

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
    if "mask_card_number" in df.columns:
        df["card_last_4"] = (
            df["mask_card_number"].astype(str).str.extract(r"(\d{4})$")  # Берёт ровно 4 цифры в конце строки
        )
    else:
        df["card_last_4"] = pd.NA

    # Приводим колонку "Дата операции" к datetime с правильным порядком день/месяц
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    # Приводим суммы к float (нормализуем запятые в точки)
    amount_cols = ["amount", "payment_amount", "cashback", "bonuses", "amount_rounded"]
    for col in amount_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False).replace("", "0").astype(float)

    return df


def _load_cache(file_path) -> Optional[Dict[str, Any]]:
    """
    Загружает кэш из JSON-файла, если он существует и не устарел.

    Логика:
        - Если файла нет — возвращает None.
        - Если файл есть, проверяет наличие поля "timestamp".
        - Вычисляет возраст кэша и сравнивает с CACHE_TTL.
        - Возвращает только данные (поле "data"), если кэш валиден.

    Параметры
    ---------
    file_path : Path
        Путь к файлу кэша.

    Возвращает
    ----------
    dict | None
        Словарь с данными кэша, если кэш валиден; иначе None.
    """
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
    """
    Сохраняет данные в JSON-файл с созданием родительских директорий.

    Перед записью создаёт все недостающие директории (parents=True).
    Данные сохраняются с отступами (indent=2) и поддержкой Unicode (ensure_ascii=False).

    Параметры
    ---------
    file_path : Path
        Полный путь к файлу кэша (включая имя файла).
    data : dict
        Данные для сохранения. Обычно ожидается структура:
        {"data": {...}, "timestamp": <float>}
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_setting(field) -> Any:
    """
    Получает значение указанного поля из файла user_settings.json.

    Логика:
        - Определяет путь к файлу настроек относительно PROJECT_ROOT.
        - Проверяет существование файла и его непустоту.
        - Читает JSON и возвращает значение по ключу.
        - По умолчанию возвращает пустой список, если ключ не найден.

    Параметры
    ---------
    field : str
        Ключ поля, которое нужно получить из настроек.

    Возвращает
    ----------
    Any
        Значение поля из JSON. Если поле не найдено — возвращается [].

    Исключения
    ----------
    FileNotFoundError
        Если файл user_settings.json не найден.
    ValueError
        Если файл настроек существует, но пустой.
    """
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


def logger(module_name: str = "no_name") -> logging.Logger:
    """
    Возвращает настроенный логгер для указанного модуля.

    Гарантирует, что к одному и тому же файлу не будет добавлено
    несколько одинаковых FileHandler (защита от дублирования строк).
    """
    logs_dir = PROJECT_ROOT / "logs"
    log_file = logs_dir / f"log_{module_name}.log"

    # Создаём папку, если её нет
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger_obj = logging.getLogger(f"Name_logger: <{module_name}>")
    logger_obj.setLevel(logging.DEBUG)

    # ПРОВЕРКА: если у этого логгера ещё нет обработчика для файла — добавляем
    if not logger_obj.handlers:
        file_handler = logging.FileHandler(
            log_file, encoding="utf-8", mode="a"
        )  # 'a' — дописывать, а не перезаписывать
        # Чуть почище формат: без лишних переносов, но с разделителем
        formatter = logging.Formatter(f"%(asctime)s | %(name)s | %(levelname)s | %(message)s\n{'=' * 60}")
        file_handler.setFormatter(formatter)
        logger_obj.addHandler(file_handler)
    else:
        # Опционально: можно вывести в консоль, что логгер уже настроен (для отладки самого логгера)
        pass
    return logger_obj


def datetime_handle(obj):
    if isinstance(obj, Timestamp):
        return obj.strftime("%Y-%m-%d")
    raise TypeError(f"Тип {type(obj)} не сериализуется")
