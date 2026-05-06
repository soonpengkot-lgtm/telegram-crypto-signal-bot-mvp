import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

WATCHLIST = {
    "core": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
    "alt":  ["ADAUSDT", "DOGEUSDT", "PEPEUSDT"],
}

TIMEFRAMES = {"direction": "4H", "structure": "1H", "confirmation": "15m"}

# Per-symbol minimum RR
RR_THRESHOLDS = {
    "BTCUSDT":  1.5,
    "ETHUSDT":  1.5,
    "SOLUSDT":  1.5,
    "XRPUSDT":  1.5,
    "ADAUSDT":  1.5,
    "DOGEUSDT": 2.0,
    "PEPEUSDT": 2.0,
}

SIGNAL_EXPIRY_HRS  = 24
MAX_DAILY_SIGNALS  = 5
RUN_INTERVAL_MIN   = 15

COOLDOWN = {
    "confirmed": 4 * 3600,
}
