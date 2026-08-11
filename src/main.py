import json

from src.utils import load_transactions
from src.views import data_to_view_page

if __name__ == "__main__":
    json_transactions = load_transactions()

    print("⚠️", json.dumps(data_to_view_page(json_transactions, "2021-12-31 15:01:01"), indent=2, ensure_ascii=False))