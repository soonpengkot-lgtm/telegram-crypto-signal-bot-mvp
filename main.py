import time
from datetime import datetime, timezone, timedelta
from bitget_api import get_candles, scan_prices
from signal_engine import analyze_symbol
from cooldown import can_send_signal, record_signal, check_invalidations, get_daily_count
from smc_analyzer import detect_market_structure
from telegram_bot import send_message, build_confirmed_message, build_invalidated_message
from logger import log_signal
from config import WATCHLIST, MAX_DAILY_SIGNALS

_MYT = timezone(timedelta(hours=8))


def _fmt(price: float) -> str:
    if price >= 1000:   return f"{price:,.2f}"
    elif price >= 1:    return f"{price:.4f}"
    else:               return f"{price:.8f}"


def get_btc_structures() -> dict:
    """Fetch BTC market structure for 15m, 1H, 4H."""
    structures = {}
    for tf, limit in [("15m", 100), ("1H", 100), ("4H", 50)]:
        try:
            candles = get_candles("BTCUSDT", tf, limit=limit)
            time.sleep(0.3)
            structures[tf] = detect_market_structure(candles)
        except Exception as e:
            print(f"  [WARN] BTC {tf} failed: {e}")
            structures[tf] = "ranging"
    print(f"  BTC | 15m:{structures['15m']} | 1H:{structures['1H']} | 4H:{structures['4H']}")
    return structures


def print_price_table(symbols: list[str], prices: dict) -> None:
    print(f"\n  {'Symbol':<12} {'Price':>14} {'24h %':>8} {'High':>14} {'Low':>14}")
    print("  " + "-" * 64)
    for sym in symbols:
        d = prices.get(sym)
        if d:
            sign = "+" if d["change24"] >= 0 else ""
            print(f"  {sym:<12} {_fmt(d['price']):>14} {sign}{d['change24']:>7.2f}% "
                  f"{_fmt(d['high24']):>14} {_fmt(d['low24']):>14}")
        else:
            print(f"  {sym:<12} {'ERROR':>14}")
    print()


def run_scan() -> None:
    all_symbols = WATCHLIST["core"] + WATCHLIST["alt"]
    now_myt     = datetime.now(_MYT).strftime("%Y-%m-%d %H:%M MYT")

    print(f"\n{'='*68}")
    print(f"  SMC Signal Scan  |  {now_myt}")
    print(f"  Daily: {get_daily_count()}/{MAX_DAILY_SIGNALS}")
    print(f"{'='*68}")

    # ── 1. Prices ─────────────────────────────────────────────────────
    print("\n[1/4] Fetching Bitget prices...")
    prices = scan_prices(all_symbols)
    print_price_table(all_symbols, prices)

    # ── 2. Invalidation check ─────────────────────────────────────────
    print("[2/4] Checking active signals...")
    invalidated, tp1_reached = check_invalidations(prices)

    for sig in tp1_reached:
        print(f"  [{sig['symbol']} {sig['direction']}] TP1 reached — removed from active.")
        log_signal(sig, signal_type="confirmed", outcome="tp1_hit")

    for sig in invalidated:
        reason = sig.get("invalidation_reason", "")
        msg    = build_invalidated_message(sig["symbol"], sig.get("direction", ""), reason)
        sent   = send_message(msg)
        print(f"  [{sig['symbol']} {sig['direction']}] Invalidated: {reason} | Sent: {sent}")
        log_signal(sig, signal_type="invalidated", outcome=reason)

    if not invalidated and not tp1_reached:
        print("  No active signals to check.")
    print()

    # ── 3. BTC structures ─────────────────────────────────────────────
    print("[3/4] BTC structure filter...")
    btc_structures = get_btc_structures()
    print()

    # ── 4. Scan symbols ───────────────────────────────────────────────
    print(f"[4/4] Scanning {len(all_symbols)} symbols (Long + Short)...\n")
    signals_sent = 0

    for symbol in all_symbols:
        print(f"  [{symbol}]")
        results = analyze_symbol(symbol, btc_structures)

        if not results:
            print(f"    No confirmed signal.\n")
            continue

        for result in results:
            direction = result["direction"]
            allowed, block_reason = can_send_signal(symbol, direction)
            if not allowed:
                print(f"    {direction.upper()} blocked: {block_reason}")
                continue

            msg  = build_confirmed_message(
                symbol=symbol, direction=direction,
                entry_zone=result["entry"],
                tp1=result["tp1"], tp2=result["tp2"], sl=result["sl"],
                conditions=result["conditions"],
            )
            sent = send_message(msg)
            if sent:
                record_signal(symbol, direction, result)
                log_signal(result, signal_type="confirmed", outcome="pending")
                signals_sent += 1
                print(f"    ✅ {direction.upper()} Confirmed | RR:{result['rr']}R | Entry:{result['entry']} | Sent")
            else:
                print(f"    Signal ready but Telegram failed.")
        print()

    # ── Summary ───────────────────────────────────────────────────────
    print(f"{'='*68}")
    print(f"  Done | New signals: {signals_sent} | Invalidated: {len(invalidated)} | TP1 hit: {len(tp1_reached)}")
    print(f"  Daily total: {get_daily_count()}/{MAX_DAILY_SIGNALS}")
    print(f"{'='*68}\n")


if __name__ == "__main__":
    run_scan()
