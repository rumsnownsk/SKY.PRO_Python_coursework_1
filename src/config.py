from pathlib import Path

# Вариант А: корень — это папка, где лежит этот файл (т.е. папка src)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CACHE_FILE_CBR = PROJECT_ROOT / "tmp" / "cache_cbr.json"
CACHE_FILE_FINNHUB = PROJECT_ROOT / "tmp" / "cache_finnhub.json"

CACHE_TTL = 3600  # 60 секунд
