# config.py
import os
from dotenv import load_dotenv

load_dotenv()

def _clean(value: str | None) -> str | None:
    """Strip spaces and quotes around keys so bad formatting doesn't break Binance."""
    if value is None:
        return None
    return value.strip().strip('"').strip("'")

# Local: from .env
API_KEY = _clean(os.getenv("BINANCE_API_KEY"))
API_SECRET = _clean(os.getenv("BINANCE_API_SECRET"))
USE_TESTNET = str(os.getenv("BINANCE_TESTNET", "true")).strip().lower() == "true"

# Deployed: override with Streamlit secrets if available
try:
    import streamlit as st

    if "BINANCE_API_KEY" in st.secrets:
        API_KEY = _clean(st.secrets["BINANCE_API_KEY"])
        API_SECRET = _clean(st.secrets["BINANCE_API_SECRET"])
        USE_TESTNET = str(
            st.secrets.get("BINANCE_TESTNET", "true")
        ).strip().lower() == "true"
except Exception:
    # when running from CLI only, streamlit import will fail – that's fine
    pass

if not (API_KEY and API_SECRET):
    raise RuntimeError("API credentials not found (.env or Streamlit secrets).")

# quick sanity check – if keys are tiny, something is wrong
if len(API_KEY) < 20 or len(API_SECRET) < 20:
    raise RuntimeError(
        f"API key/secret look too short (len={len(API_KEY)}, {len(API_SECRET)}). "
        "Check .env / secrets formatting."
    )
