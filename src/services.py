from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from pandas import DataFrame


def best_cashback_from_category(df: DataFrame, year: int, month: int) -> Dict[str, int]:
    """
    Возвращает словарь с суммарным кэшбэком по категориям за указанный месяц и год.

    Для каждой категории считается сумма кэшбэка, которая затем округляется до целого числа
    и приводится к типу int. Результат сортируется по убыванию суммы. Категории с пустым
    или нулевым кэшбэком исключаются.

    Args:
        df (DataFrame): Исходный DataFrame с транзакциями. Должен содержать колонки
            'date' (datetime) и 'cashback'.
        year (int): Год для фильтрации (целое число).
        month (int): Месяц для фильтрации (от 1 до 12).

    Returns:
        Dict[str, int]: Словарь вида {категория: суммарный кэшбэк (целое число)},
            отсортированный по убыванию суммы кэшбэка.

    Raises:
        TypeError: Если year или month не являются целыми числами, либо если year
            выходит за диапазон дат в DataFrame.
        ValueError: Если month не находится в диапазоне от 1 до 12.

    Notes:
        - Если в DataFrame нет транзакций за указанный месяц, возвращается пустой словарь ({}),
          а не список.
        - Значения кэшбэка, не являющиеся числами, обрабатываются как NaN и исключаются.
    """
    last_date = df["date"].max()
    first_date = df["date"].min()

    if not isinstance(month, int) or not isinstance(year, int):
        raise TypeError(
            f"month и year должны быть целыми числами. Последняя дата в транзакциях:{last_date.month}.{last_date.year}"
        )
    if month < 1 or month > 12:
        raise ValueError("month должен быть от 1 до 12 (включительно)")
    if year < first_date.year or year > last_date.year:
        raise TypeError(
            f"Допустимый диапазон дат: начало - {first_date.month}.{first_date.year}; "
            f"Конец - {last_date.month}.{last_date.year}"
        )

    # 1. Фильтруем ДатаФрейм по конкретному месяцу конкретного года
    filtered = df[(df["date"].dt.year == year) & (df["date"].dt.month == month)].copy()
    if filtered.empty:
        return {}

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
    Рассчитывает суммарный вклад в «Инвесткопилку» за указанный месяц при округлении
    трат до ближайшего большего значения, кратного заданному шагу.

    Для каждой подходящей транзакции вычисляется разница между округлённой суммой
    (вверх до кратного limit) и фактической суммой. Эта разница суммируется.

    Args:
        month (str): Строка с месяцем в формате 'YYYY-MM' (например, '2024-11').
        transactions (List[Dict[str, Any]]): Список словарей транзакций. Каждый словарь
            должен содержать ключи 'date' (строка 'YYYY-MM-DD') и 'amount' (число).
        limit (int): Шаг округления (например, 10, 50, 100). Должен быть положительным.

    Returns:
        float: Суммарный вклад (накопленная разница) за указанный месяц.

    Raises:
        ValueError: Если строка month имеет неверный формат или если limit <= 0.
        KeyError: Если в каком-либо словаре из transactions отсутствует ключ 'date' или 'amount'.

    Notes:
        - Округление всегда выполняется вверх до ближайшего числа, кратного limit.
        - Транзакции, дата которых не попадает в указанный месяц, игнорируются.
    """
    if limit <= 0:
        raise ValueError("limit должен быть положительным целым числом")

    target_year, target_month = map(int, month.split("-"))

    total_saved = 0.0

    for t in transactions:
        if "date" not in t or "amount" not in t:
            raise KeyError("Каждая транзакция должна содержать ключи 'date' и 'amount'")
        try:
            tx_date = datetime.strptime(t["date"], "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Неверный формат даты: {t['date']}") from e

        if tx_date.year != target_year or tx_date.month != target_month:
            continue
        amount = float(t["amount"])

        if amount <= 0:
            continue

        remainder = amount % limit
        if remainder == 0:
            rounded = amount
        else:
            rounded = amount + (limit - remainder)

        saved = rounded - amount

        total_saved += saved

    return total_saved


def get_transactions_with_phone(df_tr: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Находит транзакции, в описании которых содержится российский номер телефона,
    и возвращает их в виде списка словарей (JSON-совместимый формат).

    Поддерживаются распространённые форматы номеров: с +7 или 8, с пробелами,
    скобками, дефисами и без разделителей. Даты приводятся к строковому формату
    'YYYY-MM-DD', а пропущенные значения (NaN) заменяются на None для корректной
    сериализации в JSON.

    Args:
        df_tr (pd.DataFrame): DataFrame с транзакциями. Ожидается наличие колонки
            'description' (для поиска номера) и опционально 'date'.

    Returns:
        List[Dict[str, Any]]: Список словарей с отфильтрованными транзакциями.
            Если подходящих транзакций нет или колонки 'description' не существует,
            возвращается пустой список ([]).

    Notes:
        - Регулярное выражение настроено на поиск российских мобильных номеров.
        - Все нечисловые значения в датах приводятся к NaT и затем конвертируются в None.
    """
    pattern = r"(?:\+?7|8)[\s\-()]*\d{3}[\s\-()]*\d{2,3}[\s\-()]*\d{2}[\s\-()]*\d{2}"

    # Защита: если колонки нет — сразу пустой список
    if "description" not in df_tr.columns:
        return []

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

    # Заменяем NaN на None для JSON-совместимости
    with_phone = with_phone.where(pd.notnull(with_phone), None)

    return with_phone.to_dict(orient="records")


def get_transfer(df_tr: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Фильтрует транзакции, относящиеся к переводам между людьми, где в описании
    присутствует имя и инициал (формат: слово + пробел + заглавная буква + точка).

    Отбираются строки, где категория содержит подстроку «Переводы» и описание
    соответствует шаблону имени и инициала. Даты приводятся к формату 'YYYY-MM-DD',
    а пропущенные значения заменяются на None.

    Args:
        df_tr (pd.DataFrame): DataFrame с транзакциями. Должны присутствовать
            колонки 'category' и 'description', а также опционально 'date'.

    Returns:
        List[Dict[str, Any]]: Список словарей с подходящими транзакциями.
            Если совпадений нет, возвращается пустой список ([]).

    Notes:
        - Поиск в категории выполняется с учётом подстроки «Переводы» (регистронезависимо).
        - Шаблон в описании рассчитан на формат вроде «Иван И.», «Сергей П.» и т.п.
    """
    pattern = r"\w+\s+[А-ЯЁ]\."

    cat_mask = df_tr["category"].str.contains("Переводы", regex=False, na=False)
    desc_mask = df_tr["description"].str.contains(pattern, regex=True, na=False)

    with_transfer = df_tr[cat_mask & desc_mask].copy()

    if "date" in with_transfer.columns:
        # Сначала убедимся, что колонка datetime, потом конвертируем в строку
        if not pd.api.types.is_datetime64_any_dtype(with_transfer["date"]):
            with_transfer["date"] = pd.to_datetime(with_transfer["date"], errors="coerce")
        with_transfer["date"] = with_transfer["date"].dt.strftime("%Y-%m-%d")

    with_transfer = with_transfer.where(pd.notnull(with_transfer), None)

    return with_transfer.to_dict(orient="records")
