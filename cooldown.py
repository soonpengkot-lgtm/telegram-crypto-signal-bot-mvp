import json
import os
from datetime import datetime, timezone, timedelta
from config import COOLDOWN, MAX_DAILY_SIGNALS

_STATE_FILE = os.path.join("data", "state.json")


def _load() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE) as f:
            return json.load(f)
    return {"cooldowns": {}, "daily_counts": {}, "active_signals": []}


def _save(state: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def can_send_signal(symbol: str, direction: str) -> tuple[bool, str]:
    state = _load()
    now   = datetime.now(timezone.utc)

    daily = state["daily_counts"].get(_today(), 0)
    if daily >= MAX_DAILY_SIGNALS:
        return False, f"Daily limit reached ({MAX_DAILY_SIGNALS}/day)"

    key            = f"{symbol}_{direction}"
    cooldown_until = state["cooldowns"].get(key)
    if cooldown_until:
        until_dt = datetime.fromisoformat(cooldown_until)
        if now < until_dt:
            mins = int((until_dt - now).total_seconds() / 60)
            return False, f"Cooldown: {mins}m remaining"

    return True, ""


def record_signal(symbol: str, direction: str, signal_data: dict) -> None:
    state = _load()
    now   = datetime.now(timezone.utc)

    key   = f"{symbol}_{direction}"
    until = now + timedelta(seconds=COOLDOWN["confirmed"])
    state["cooldowns"][key] = until.isoformat()

    today = _today()
    state["daily_counts"][today] = state["daily_counts"].get(today, 0) + 1

    state["active_signals"].append({
        **signal_data,
        "expires_at": (now + timedelta(hours=24)).isoformat(),
    })
    _save(state)


def check_invalidations(current_prices: dict) -> tuple[list[dict], list[dict]]:
    """
    Check active signals against current prices.
    Returns (invalidated, tp1_reached):
      - invalidated: SL hit or 24h expired without TP1
      - tp1_reached: TP1 hit (success — no alert, just remove)
    """
    state        = _load()
    now          = datetime.now(timezone.utc)
    invalidated  = []
    tp1_reached  = []
    still_active = []

    for sig in state.get("active_signals", []):
        symbol    = sig["symbol"]
        direction = sig.get("direction", "long")
        sl_raw    = sig.get("sl_raw", 0)
        tp1_raw   = sig.get("tp1_raw", 0)
        expires   = datetime.fromisoformat(sig["expires_at"])
        pd        = current_prices.get(symbol)
        price     = pd["price"] if pd else 0

        if price == 0:
            still_active.append(sig)
            continue

        sl_hit  = (direction == "long"  and price < sl_raw) or \
                  (direction == "short" and price > sl_raw)
        tp1_hit = (direction == "long"  and price >= tp1_raw) or \
                  (direction == "short" and price <= tp1_raw)
        expired = now > expires

        if tp1_hit:
            tp1_reached.append(sig)
        elif sl_hit:
            sig["invalidation_reason"] = f"Hit SL {sig['sl']}"
            invalidated.append(sig)
        elif expired:
            sig["invalidation_reason"] = "24h 未达 TP1 — signal expired"
            invalidated.append(sig)
        else:
            still_active.append(sig)

    if len(still_active) != len(state.get("active_signals", [])):
        state["active_signals"] = still_active
        _save(state)

    return invalidated, tp1_reached


def get_daily_count() -> int:
    return _load()["daily_counts"].get(_today(), 0)
