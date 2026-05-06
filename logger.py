import csv
import os
from datetime import datetime, timezone, timedelta

_LOG_FILE = os.path.join("data", "signals_log.csv")
_MYT      = timezone(timedelta(hours=8))

HEADERS = [
    "timestamp_myt", "symbol", "signal_type", "direction",
    "entry", "tp1", "tp2", "sl", "rr", "conditions", "outcome",
]


def log_signal(signal_data: dict, signal_type: str = "confirmed", outcome: str = "pending") -> None:
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.exists(_LOG_FILE) and os.path.getsize(_LOG_FILE) > 0
    row = {
        "timestamp_myt": datetime.now(_MYT).strftime("%Y-%m-%d %H:%M MYT"),
        "symbol":        signal_data.get("symbol", ""),
        "signal_type":   signal_type,
        "direction":     signal_data.get("direction", ""),
        "entry":         signal_data.get("entry", ""),
        "tp1":           signal_data.get("tp1", ""),
        "tp2":           signal_data.get("tp2", ""),
        "sl":            signal_data.get("sl", ""),
        "rr":            signal_data.get("rr", ""),
        "conditions":    "|".join(signal_data.get("conditions", [])),
        "outcome":       outcome,
    }
    with open(_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
