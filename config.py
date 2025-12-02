# config.py
import os
from dotenv import load_dotenv

# For local runs: load values from .env
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

# On Streamlit Cloud we use st.secrets instead of .env
try:
    import streamlit as st

    # If these keys exist in secrets, override the env values
    if "BINANCE_API_KEY" in st.secrets:
        API_KEY = st.secrets["BINANCE_API_KEY"]
        API_SECRET = st.secrets["BINANCE_API_SECRET"]
        USE_TESTNET = str(st.secrets.get("BINANCE_TESTNET", "true")).lower() == "true"
except Exception:
    # When running from CLI (no streamlit), this import fails
    pass

if not (API_KEY and API_SECRET):
    # If we reach here, neither .env nor secrets are set correctly
    raise RuntimeError(
        "API credentials not found. Use .env locally or Streamlit secrets in deployment."
    )
