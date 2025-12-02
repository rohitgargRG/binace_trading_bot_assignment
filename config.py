import os
from dotenv import load_dotenv

load_dotenv()  # loads from .env

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    raise ValueError("API key/secret missing. Set them in .env")
