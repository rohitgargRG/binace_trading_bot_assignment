# config.py
import os
from dotenv import load_dotenv

# load .env once at startup
load_dotenv()

# pull API keys from the environment
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# simple flag to switch between testnet/mainnet
# default stays True because this project is for testnet
USE_TESTNET = os.getenv("BINANCE_TESTNET", "true").strip().lower() == "true"

# quick sanity check so the app fails early if keys are missing
if not API_KEY or not API_SECRET:
    raise RuntimeError("Missing API key/secret. Make sure .env is set correctly.")
