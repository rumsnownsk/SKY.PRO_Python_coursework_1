import pytest

from src.services import *


@pytest.fixture
def sample_transactions_df():
    df = pd.DataFrame({
        "date": [
            "2024-10-05", "2024-10-15", "2024-11-03", "2024-11-20",
            "2024-11-25", "2024-12-01"
        ],
        "category": [
            "Продукты", "Продукты", "Переводы", "Переводы",
            "Электроника", "Продукты"
        ],
        "description": [
            "Покупка в магазине",
            "+7 900 111-22-33 доставка",
            "Иван И.",
            "Мария П.",
            "Оплата заказа",
            "89990001122 курьер"
        ],
        "cashback": [120.4, 80.6, 0, 50.1, 300.9, 25.3],
        "amount": [-1200, -800, -5000, -3000, -20000, -300]
    })
    df["date"] = pd.to_datetime(df["date"])
    return df


@pytest.fixture
def transactions_list():
    return [
        {"date": "2024-11-05", "amount": 1200},
        {"date": "2024-11-10", "amount": 850},
        {"date": "2024-11-20", "amount": 950},
        {"date": "2024-10-05", "amount": 500},  # не тот месяц
    ]


def test_best_cashback_from_category(sample_transactions_df):
    result = best_cashback_from_category(sample_transactions_df, 2024, 11)
    assert isinstance(result, dict)
    assert result == {"Электроника": 301, "Переводы": 50}

    assert best_cashback_from_category(sample_transactions_df, 2024, 12) == {"Продукты": 25}

    without_nov = sample_transactions_df[sample_transactions_df["date"].dt.month != 11]
    empty_cashback = best_cashback_from_category(without_nov, 2024, 11)
    assert empty_cashback == {}

    df = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "cashback": [10]})
    with pytest.raises(TypeError):
        best_cashback_from_category(df, 2024, "11")

    with pytest.raises(ValueError):
        best_cashback_from_category(df, 2024, 13)


def test_investment_bank(transactions_list):
    result_100 = investment_bank("2024-11", transactions_list, 100)
    assert result_100 == 100.0

    result_no_match = investment_bank("2023-11", transactions_list, 100)
    assert result_no_match == 0.0

    with pytest.raises(ValueError):
        investment_bank("2024-11", transactions_list, 0)

    with pytest.raises(ValueError):
        investment_bank("2024-11", [{"date": "", "amount": ""}], 100)


def test_get_transactions_with_phone(sample_transactions_df):
    result_norm = get_transactions_with_phone(sample_transactions_df)

    assert len(result_norm) == 2
    assert isinstance(result_norm, list)
    descriptions = [el["description"] for el in result_norm]

    assert any("+7" in d for d in descriptions)
    assert any("8" in d and len(d)>5 for d in descriptions)

    df_no_phone = pd.DataFrame([{"columns": "any"}])
    result_no_phone = get_transactions_with_phone(df_no_phone)
    assert result_no_phone == []


def test_get_transfer(sample_transactions_df):
    result = get_transfer(sample_transactions_df)
    assert len(result) == 2
    assert isinstance(result, list)

    df = sample_transactions_df.copy()
    df.loc[2, "category"] = "переводы"  # строчная буква
    assert len(get_transfer(df)) >= 1

    df_other = sample_transactions_df.copy()
    df_other["category"] = "Другое"
    assert get_transfer(df_other) == []

    for row in result:
        assert isinstance(row["date"], str) or row["date"] is None





