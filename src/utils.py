from pathlib import Path
from typing import List, Dict, Any

from pandas import isna

from src.config import PROJECT_ROOT

import pandas as pd


def xlsx_to_json(filename: str, base_dir: Path | None = None) -> list[Any] | str:
    """
    Читает Excel-файл и возвращает список словарей (транзакций), просто конвертируя данные в удобный json-формат
    :param filename:
    :param base_dir:
    :return:
    """
    # определяем путь головной директории проекта
    root_dir = base_dir if base_dir else PROJECT_ROOT

    file_path = root_dir / "data" / filename

    if not file_path.exists():
        print(f'файл не найден: {file_path}')
        return []

    if file_path.stat().st_size == 0:
        print("файл пустой")
        return []

    try:
        df = pd.read_excel(file_path, nrows=5)
    except Exception as e:
        print(f"Ошибка чтения: {e}")
        return []

    if df.empty:
        print('xlsx‑файл %s не содержит данных')
        return []

    return df.to_dict(orient="records")






        # transactions.append(row)

    # print(df.shape)
