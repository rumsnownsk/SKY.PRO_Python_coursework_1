import json
import os
from datetime import timedelta

import pandas as pd
import pytest

from src.reports import _prepare_for_json, spending_by_category, spending_by_weekday

TMP_DIR = "tmp"


@pytest.fixture
def sample_transactions():
    df = pd.DataFrame(
        {
            "date": [
                pd.Timestamp("2024-11-20"),  # попадает, категория Продукты
                pd.Timestamp("2024-11-10"),  # попадает, категория Продукты
                pd.Timestamp("2024-10-11"),  # попадает, категория Продукты
                pd.Timestamp("2024-07-22"),  # НЕ попадает (старше 3 месяцев)
            ],
            "category": ["Продукты", "Продукты", "Продукты", "Продукты"],
            "amount": [100.0, 200.0, 150.0, 500.0],
            "description": ["Хлеб", "Молоко", "Заказ", "Старый заказ"],
        }
    )
    return df


# @pytest.fixture(autouse=True)
# def cleanup_tmp():
#     """Удаляет папку tmp после каждого теста, чтобы не накапливались файлы."""
#     yield
#     if os.path.exists(TMP_DIR):
#         for fname in os.listdir(TMP_DIR):
#             os.remove(os.path.join(TMP_DIR, fname))
#         os.rmdir(TMP_DIR)


def test_prepare_for_json_converts_timestamp_and_nan():
    df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-01"), pd.NaT],
            "amount": [10.5, float("nan")],
            "category": ["A", "B"],
        }
    )
    result = _prepare_for_json(df)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["date"] == "2024-01-01"
    assert result[1]["date"] is None
    assert result[1]["amount"] is None


def test_prepare_for_json_raises_on_non_dataframe():
    with pytest.raises(TypeError):
        _prepare_for_json("не DataFrame")


def test_spending_by_category(sample_transactions):
    ref_date = pd.Timestamp("2024-11-20")
    result = spending_by_category(sample_transactions, "продукты", date=str(ref_date.date()))

    assert isinstance(result, pd.DataFrame)
    # Теперь ожидаем 3 строки: 20.11, 10.11 и 11.10 (все попадают в 3 месяца и категорию)
    assert len(result) == 3

    dates_list = [d.date() for d in result["date"]]
    expected = [
        ref_date.date(),  # 2024-11-20
        (ref_date - timedelta(days=10)).date(),  # 2024-11-10
        (ref_date - timedelta(days=40)).date(),  # 2024-10-11
    ]
    assert dates_list == expected
    # assert result_empty.empty


def test_spending_by_weekday_returns_avg_by_day(sample_transactions):
    ref_date = pd.Timestamp("2024-11-20")  # среда
    result = spending_by_weekday(sample_transactions, date=str(ref_date.date()))

    assert isinstance(result, pd.DataFrame)
    assert set(result.columns) == {"weekday", "avg_amount"}
    assert not result.empty


def test_spending_by_weekday_handles_invalid_dates(sample_transactions):
    df = sample_transactions.copy()
    df.loc[0, "date"] = pd.NaT  # удалим одну дату
    result = spending_by_weekday(df)

    # Функция должна отбросить строки с NaT и посчитать по оставшимся
    assert isinstance(result, pd.DataFrame)
    assert set(result.columns) == {"weekday", "avg_amount"}


def test_spending_by_weekday_saves_json(sample_transactions):
    spending_by_weekday(sample_transactions)
    file_path = os.path.join(TMP_DIR, "report_spending_by_weekday.json")
    assert os.path.exists(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
