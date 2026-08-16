import pandas as pd

from src.views import *


def test_get_greeting():
    morning_time = "2020-11-30 10:01:01"
    evening_time = "2020-11-30 20:01:01"
    error_time = "2020.11.30 10.01.01"
    assert get_greeting(morning_time) == "Доброе утро"
    assert get_greeting(evening_time) == "Добрый вечер"
    assert get_greeting(error_time) == "Доброго времени суток!"

def test_get_transactions_by_date_range_df():
    user_df = pd