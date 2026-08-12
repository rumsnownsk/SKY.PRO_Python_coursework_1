import json
import time

import requests
import pandas as pd

from datetime import datetime
from typing import List, Dict, Any, Hashable, Tuple
from pandas import DataFrame

from src.config import PROJECT_ROOT, CACHE_FILE_CBR
from src.utils import load_transactions, _save_cache, _load_cache

# Кэш: храним весь ответ ЦБ целиком + время запроса
_cbr_cache: Dict[str, Any] = {}
CACHE_TTL = 60  # 1 минута


def data_to_view_page(df: DataFrame, datetime_str):
    # Получение ДатаФрейма транзакций с начала месяца до даты, указанной пользователем
    transactions_by_range = get_transactions_by_date_range_df(df, datetime_str)

    cards_data = group_transactions_by_cards(transactions_by_range)
    top_transactions = get_top_n_expensive_transactions(transactions_by_range)
    currency_rates = get_currency_rates()

    return {
        "greeting": get_greeting(datetime_str),
        "cards": cards_data,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        # "stock_prices": card_last_4,
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
    user_currencies = user_settings.get("user_currencies", [])

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
        _save_cache(file_path=CACHE_FILE_CBR, data=cbr_data)
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
                # "from_cache": from_cache
            })
        else:
            pass

    return current_courses


if __name__ == "__main__":
    # print(get_greeting("2021-12-25 15:01:01"))
    print(json.dumps(data_to_view_page(load_transactions(), "2021-12-31 15:01:01"), indent=2, ensure_ascii=False))
    # group_transactions_by_cards(load_transactions())
