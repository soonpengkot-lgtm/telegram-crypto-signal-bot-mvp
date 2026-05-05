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
    """Returns (allowed, block_reason). Empty reason means allowed."""
    state = _load()
    now   = datetime.now(timezone.utc)

    # Daily limit
    daily = state["daily_counts"].get(_today(), 0)
    if daily >= MAX_DAILY_SIGNALS:
        return False, f"Daily limit reached ({MAX_DAILY_SIGNALS}/day)"

    # Cooldown per symbol+direction
    key            = f"{symbol}_{direction}"
    cooldown_until = state["cooldowns"].get(key)
    if cooldown_until:
        until_dt = datetime.fromisoformat(cooldown_until)
        if now < until_dt:
            mins = int((until_dt - now).total_seconds() / 60)
            return False, f"Cooldown: {mins}m remaining"

    return True, ""


def record_signal(symbol: str, direction: str, signal_data: dict) -> None:
    """Record a sent signal: update cooldown, daily count, and active signal list."""
    state = _load()
    now   = datetime.now(timezone.utc)

    key = f"{symbol}_{direction}"
    until = now + timedelta(seconds=COOLDOWN["confirmed"])
    state["cooldowns"][key] = until.isoformat()

    today = _today()
    state["daily_counts"][today] = state["daily_counts"].get(today, 0) + 1

    state["active_signals"].append({
        **signal_data,
        "expires_at": (now + timedelta(hours=24)).isoformat(),
    })

    _save(state)


def check_invalidations(current_prices: dict) -> list[dict]:
    """
    Compare active signals against current prices.
    Returns list of signals invalidated (SL broken or expired after 24h).
    Removes invalidated signals from state.
    """
    state        = _load()
    now          = datetime.now(timezone.utc)
    invalidated  = []
    still_active = []

    for sig in state.get("active_signals", []):
        symbol   = sig["symbol"]
        sl_raw   = sig.get("sl_raw", 0)
        expires  = datetime.fromisoformat(sig["expires_at"])
        price_data = current_prices.get(symbol)
        current    = price_data["price"] if price_data else 0

        if now > expires:
            sig["invalidation_reason"] = "超过 24h 未确认"
            invalidated.append(sig)
        elif sl_raw > 0 and current > 0 and current < sl_raw:
            sig["invalidation_reason"] = f"跌破 SL {sig['sl']}"
            invalidated.append(sig)
        else:
            still_active.append(sig)

    if len(still_active) != len(state.get("active_signals", [])):
        state["active_signals"] = still_active
        _save(state)

    return invalidated


def get_daily_count() -> int:
    return _load()["daily_counts"].get(_today(), 0)
