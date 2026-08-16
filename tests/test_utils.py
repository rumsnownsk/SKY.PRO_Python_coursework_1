import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.config import CACHE_TTL
from src.utils import _load_cache, _save_cache, load_transactions


@pytest.fixture
def mock_project_root(tmp_path: Path):
    # Подменяем PROJECT_ROOT на временную папку
    with patch("src.utils.PROJECT_ROOT", tmp_path):
        yield tmp_path


def test_load_transactions_success(mock_project_root: Path):
    data_dir = mock_project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    df_raw = pd.DataFrame(
        {
            "Дата операции": ["01.11.2020 10:00:00", "02.11.2020 12:30:00"],
            "Номер карты": ["*1234", "*5678"],
            "Сумма операции": ["100,50", "-200,00"],
            "Кэшбэк": ["10,0", "0"],
            "Категория": ["Еда", "Транспорт"],
        }
    )
    file_path = data_dir / "operations.xlsx"
    df_raw.to_excel(file_path, index=False)

    result = load_transactions(filename="operations.xlsx")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "card_last_4" in result.columns
    assert result["card_last_4"].tolist() == ["1234", "5678"]
    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert result["amount"].tolist() == [100.5, -200.0]
    assert result["cashback"].tolist() == [10.0, 0.0]


def test_load_transactions_file_not_found(mock_project_root: Path):
    with pytest.raises(FileNotFoundError, match="Файл не найден"):
        load_transactions(filename="nonexistent.xlsx")


def test_load_transactions_empty_file(mock_project_root: Path):
    data_dir = mock_project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    empty_file = data_dir / "empty.xlsx"
    empty_file.write_bytes(b"")  # пустой файл

    with pytest.raises(ValueError, match="пустой"):
        load_transactions(filename="empty.xlsx")


def test_load_transactions_missing_columns(mock_project_root: Path):
    """Проверяем, что функция не падает, если некоторых колонок нет, но корректно обрабатывает то, что есть."""
    data_dir = mock_project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    df_raw = pd.DataFrame(
        {
            "Дата операции": ["01.11.2020"],
            # нет суммы, нет карты — проверим поведение
        }
    )
    file_path = data_dir / "minimal.xlsx"
    df_raw.to_excel(file_path, index=False)

    result = load_transactions(filename="minimal.xlsx")
    assert isinstance(result, pd.DataFrame)
    assert "date" in result.columns
    # card_last_4 должен быть, но может быть NaN, если не из чего извлечь
    assert "card_last_4" in result.columns


@pytest.fixture
def cache_file(tmp_path: Path):
    return tmp_path / "cache.json"


def test__save_cache_and__load_cache_valid(cache_file: Path):
    data = {"data": {"Valute": {"USD": {"Value": 75}}}, "timestamp": time.time()}
    _save_cache(cache_file, data)

    loaded = _load_cache(cache_file)
    assert loaded == data["data"]


def test__load_cache_expired(cache_file: Path):
    now = time.time()
    expired_data = {
        "data": {"Valute": {"EUR": {"Value": 85}}},
        "timestamp": now - (CACHE_TTL + 60),  # явно просрочено
    }
    _save_cache(cache_file, expired_data)

    loaded = _load_cache(cache_file)
    assert loaded is None


def test__load_cache_no_timestamp(cache_file: Path):
    no_ts_data = {"data": {"USD": 70}}
    _save_cache(cache_file, no_ts_data)

    loaded = _load_cache(cache_file)
    assert loaded is None


def test__load_cache_invalid_json(cache_file: Path):
    cache_file.write_text("not json at all")
    loaded = _load_cache(cache_file)
    assert loaded is None


def test__load_cache_file_missing():
    fake_path = Path("/nonexistent/cache.json")
    loaded = _load_cache(fake_path)
    assert loaded is None
