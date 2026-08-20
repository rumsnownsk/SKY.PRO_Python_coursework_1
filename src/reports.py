import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_REPORT_FILENAME = "report_spending.json"


def save_report(filename: Optional[str] = None):
    """
    Декоратор для сохранения результата функции (DataFrame) в JSON-файл.

    Если декорированная функция возвращает pandas.DataFrame, он конвертируется
    в список словарей (JSON-совместимый формат) и сохраняется в папку 'tmp'.
    Даты приводятся к строкам '%Y-%m-%d', NaN заменяются на None.

    Args:
        filename (Optional[str]): Имя файла для сохранения. Если не передано,
            используется DEFAULT_REPORT_FILENAME ('report_spending.json').

    Returns:
        Callable: Декоратор, который оборачивает функцию.

    Notes:
        - Папка 'tmp' создаётся автоматически (exist_ok=True).
        - Любые ошибки при записи в файл молча игнорируются (try/except).
        - Если результат функции не является DataFrame, декоратор просто возвращает
          результат без сохранения.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info("Запуск декорированной функции: %s", func.__name__)

            # 1. Сначала запускаем саму функцию и получаем результат (DataFrame)
            result = func(*args, **kwargs)

            if not isinstance(result, pd.DataFrame):
                return result

            # 2. Выбираем имя файла
            target_filename = filename if filename else DEFAULT_REPORT_FILENAME

            # 3. Готовим данные, чтобы json.dump не упал на датах и NaN
            data_to_save = _prepare_for_json(result)

            # 4. сохраняем в папку
            os.makedirs("tmp", exist_ok=True)
            full_path = os.path.join("tmp", target_filename)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, ensure_ascii=False)
                logger.info("Отчёт сохранён: %s (строк: %d)", full_path, len(data_to_save))

            except Exception as e:
                logger.error("Не удалось сохранить отчёт в %s: %s", full_path, e)
                raise RuntimeError(f"Failed to save report: {e}") from e

            return result

        return wrapper

    return decorator


def _prepare_for_json(data: Any) -> Any:
    """
    Преобразует pandas.DataFrame в список словарей, пригодный для json.dump.

    Выполняет следующие преобразования:
      - pandas.Timestamp → строка '%Y-%m-%d' или None, если значение пропущено.
      - float NaN → None (чтобы в JSON стал null).
      - Остальные значения остаются без изменений.

    Args:
        data (Any): Ожидаемый вход — pandas.DataFrame.

    Returns:
        List[Dict]: Список словарей с очищенными значениями.

    Raises:
        TypeError: Если переданный объект не является DataFrame.
    """
    if not isinstance(data, pd.DataFrame):
        logger.error("_prepare_for_json вызван не с DataFrame: %s", type(data).__name__)
        raise TypeError(f"_prepare_for_json ожидает DataFrame, получено {type(data).__name__}")

    records = data.to_dict(orient="records")
    cleaned: List[Dict[str, Any]] = []

    for row in records:
        clean_row = {}
        for k, v in row.items():
            # Явная обработка pd.NaT (это отдельный тип, который не является Timestamp)
            if v is pd.NaT or (isinstance(v, pd.Timestamp) and pd.isna(v)):
                clean_row[k] = None
            elif isinstance(v, pd.Timestamp):
                clean_row[k] = v.strftime("%Y-%m-%d")
            elif isinstance(v, float) and pd.isna(v):
                clean_row[k] = None
            else:
                clean_row[k] = v
        cleaned.append(clean_row)
    logger.debug("JSON-подготовка завершена: %d записей", len(cleaned))
    return cleaned


@save_report("report_spending_by_category.json")
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Преобразует pandas.DataFrame в список словарей, пригодный для json.dump.

    Выполняет следующие преобразования:
      - pandas.Timestamp → строка '%Y-%m-%d' или None, если значение пропущено.
      - float NaN → None (чтобы в JSON стал null).
      - Остальные значения остаются без изменений.

    Args:
        data (Any): Ожидаемый вход — pandas.DataFrame.

    Returns:
        List[Dict]: Список словарей с очищенными значениями.

    Raises:
        AttributeError: Если у переданного объекта нет метода .to_dict (не DataFrame).
    """
    if transactions.empty:
        logger.warning("spending_by_category: входной DataFrame пуст, возвращаем пустой результат")
        return pd.DataFrame()

    # устанавливаем даты начала и конца периода
    if date is None:
        ref_date = pd.Timestamp.today()
    else:
        try:
            ref_date = pd.to_datetime(date)
        except (ValueError, TypeError):
            logger.warning("Неверный формат даты '%s', используется текущая дата.", date)
            ref_date = pd.Timestamp.today()

    start_date = ref_date - pd.DateOffset(months=3)
    logger.info(
        "spending_by_category: фильтр по датам [%s, %s], категория содержит '%s'",
        start_date.date(),
        ref_date.date(),
        category,
    )
    # фильтруем данные по периоду и категории
    mask_date = (transactions["date"] >= start_date) & (transactions["date"] <= ref_date)
    mask_category = transactions["category"].str.contains(category, case=False, na=False)

    # получаем новый датафрейм
    res_df = transactions[mask_date & mask_category].copy()

    if not res_df.empty:
        res_df = res_df.sort_values(by="date", ascending=False)
    logger.info("spending_by_category: отфильтровано %d строк (из %d)", len(res_df), len(transactions))
    return res_df


@save_report("report_spending_by_weekday.json")
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает DataFrame со средним чеком по дням недели за последние 3 месяца.

    Для каждой транзакции вычисляется день недели, затем считается среднее значение
    по колонке 'amount' для каждого дня. Результат содержит колонки
    ['weekday', 'avg_amount'].

    Args:
        transactions (pd.DataFrame): Исходный DataFrame с транзакциями.
            Должна быть колонка 'date' и 'amount'.
        date (Optional[str], optional): Дата отсчёта. Если не указана,
            используется текущая дата.

    Returns:
        pd.DataFrame: DataFrame с колонками ['weekday', 'avg_amount'],
            либо пустой DataFrame с этими колонками, если данных нет.
    """
    if transactions.empty:
        return pd.DataFrame(columns=["weekday", "avg_amount"])

    if date is None:
        ref_date = pd.Timestamp.today()
    else:
        try:
            ref_date = pd.to_datetime(date)
        except (ValueError, TypeError):
            logger.warning("spending_by_weekday: неверный формат даты '%s', используем текущую дату", date)
            ref_date = pd.Timestamp.today()
    start_date = ref_date - pd.DateOffset(months=3)

    logger.info("spending_by_weekday: фильтр по датам [%s, %s]", start_date.date(), ref_date.date())

    df = transactions.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Убираем строки, где дата не распарсилась (NaN)
    df = df.dropna(subset=["date"])

    mask = (df["date"] >= start_date) & (df["date"] <= ref_date)
    filtered = df[mask].copy()

    if filtered.empty:
        logger.info("spending_by_weekday: после фильтрации данных нет, возвращаем пустой DataFrame")
        return pd.DataFrame(columns=["weekday", "avg_amount"])

    day_map = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"}
    filtered["weekday"] = filtered["date"].dt.dayofweek.map(day_map)

    result = (
        filtered.groupby("weekday", sort=False)["amount"].mean().reset_index().rename(columns={"amount": "avg_amount"})
    )
    logger.info("spending_by_weekday: рассчитано среднее по %d дням недели", len(result))
    return result
