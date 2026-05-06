import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

WATCHLIST = {
    "core": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
    "alt":  ["ADAUSDT", "DOGEUSDT", "PEPEUSDT"],
}

# Timeframes: 4H = direction filter, 1H = structure/POI, 15m = confirmation
TIMEFRAMES = {"direction": "4H", "structure": "1H", "confirmation": "15m"}

MIN_RR             = 1.5   # minimum RR for Confirmed signal
SIGNAL_EXPIRY_HRS  = 24    # auto-invalidate after N hours
MAX_DAILY_SIGNALS  = 5     # max Confirmed signals sent per day
RUN_INTERVAL_MIN   = 15    # scan runs every 15 minutes (via scheduler)

COOLDOWN = {
    "confirmed": 4 * 3600,  # same symbol + direction: cooldown 4 hours
}
