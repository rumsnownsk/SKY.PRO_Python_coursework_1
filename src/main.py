import json

from dotenv import load_dotenv

from src.utils import load_transactions
from src.views import data_for_view_page

if __name__ == "__main__":
    # загрузка библиотеки dotenv()
    load_dotenv()

    json_transactions = load_transactions()

    print("⚠️", json.dumps(data_for_view_page(json_transactions, "2021-12-31 15:01:01"), indent=2, ensure_ascii=False))