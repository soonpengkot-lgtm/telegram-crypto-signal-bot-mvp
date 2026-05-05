import time
from datetime import datetime, timezone
from bitget_api import get_candles, scan_prices
from signal_engine import analyze_symbol
from cooldown import can_send_signal, record_signal, check_invalidations, get_daily_count
from smc_analyzer import detect_market_structure
from telegram_bot import send_message, build_confirmed_message, build_invalidated_message
from config import WATCHLIST, MAX_DAILY_SIGNALS


def _fmt(price: float) -> str:
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    else:
        return f"{price:.8f}"


def get_btc_4h_structure() -> str:
    try:
        candles = get_candles("BTCUSDT", "4H", limit=50)
        struct  = detect_market_structure(candles)
        print(f"  BTC 4H: {struct.upper()}")
        return struct
    except Exception as e:
        print(f"  [WARN] BTC 4H fetch failed: {e}")
        return "ranging"


def print_price_table(symbols: list[str], prices: dict) -> None:
    print(f"\n  {'Symbol':<12} {'Price':>14} {'24h %':>8} {'24h High':>14} {'24h Low':>14}")
    print("  " + "-" * 64)
    for sym in symbols:
        d = prices.get(sym)
        if d:
            sign = "+" if d["change24"] >= 0 else ""
            print(
                f"  {sym:<12} {_fmt(d['price']):>14} "
                f"{sign}{d['change24']:>7.2f}% "
                f"{_fmt(d['high24']):>14} "
                f"{_fmt(d['low24']):>14}"
            )
        else:
            print(f"  {sym:<12} {'ERROR':>14}")
    print()


def run_scan() -> None:
    all_symbols = WATCHLIST["core"] + WATCHLIST["alt"]
    now_str     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"\n{'='*68}")
    print(f"  SMC Confirmed Signal Scan  |  {now_str}")
    print(f"  Daily signals sent: {get_daily_count()}/{MAX_DAILY_SIGNALS}")
    print(f"{'='*68}")

    # ── Step 1: Current prices ─────────────────────────────────────────
    print("\n[1/4] Fetching Bitget prices...")
    prices = scan_prices(all_symbols)
    print_price_table(all_symbols, prices)

    # ── Step 2: Invalidation check ────────────────────────────────────
    print("[2/4] Checking active signal invalidations...")
    invalidated = check_invalidations(prices)
    if not invalidated:
        print("  No active signals to check.\n")
    for sig in invalidated:
        reason = sig.get("invalidation_reason", "Unknown")
        msg    = build_invalidated_message(sig["symbol"], reason=reason)
        sent   = send_message(msg)
        print(f"  [{sig['symbol']}] Invalidated — {reason} | Telegram: {sent}\n")

    # ── Step 3: BTC 4H direction filter ──────────────────────────────
    print("[3/4] BTC 4H direction filter...")
    btc_structure = get_btc_4h_structure()
    print()

    # ── Step 4: Scan symbols ──────────────────────────────────────────
    print(f"[4/4] Scanning {len(all_symbols)} symbols for SMC Confirmed setups...\n")
    signals_sent = 0

    for symbol in all_symbols:
        print(f"  [{symbol}]")

        result = analyze_symbol(symbol, btc_4h_structure=btc_structure)
        if result is None:
            print(f"    No confirmed signal.\n")
            continue

        # Cooldown + daily limit gate
        allowed, block_reason = can_send_signal(symbol, result["direction"])
        if not allowed:
            print(f"    Signal found but blocked: {block_reason}\n")
            continue

        # Send Confirmed signal
        msg = build_confirmed_message(
            symbol=result["symbol"],
            direction=result["direction"],
            entry_zone=result["entry"],
            tp1=result["tp1"],
            tp2=result["tp2"],
            sl=result["sl"],
        )
        sent = send_message(msg)
        if sent:
            record_signal(symbol, result["direction"], result)
            signals_sent += 1
            print(f"    SMC Confirmed ✅ | RR: {result['rr']}R | Entry: {result['entry']} | Telegram: sent\n")
        else:
            print(f"    Signal ready but Telegram failed.\n")

        time.sleep(0.5)

    # ── Summary ───────────────────────────────────────────────────────
    print(f"{'='*68}")
    print(f"  Done. New confirmed signals: {signals_sent} | Invalidations: {len(invalidated)}")
    print(f"  Daily total: {get_daily_count()}/{MAX_DAILY_SIGNALS}")
    print(f"{'='*68}\n")


if __name__ == "__main__":
    run_scan()
