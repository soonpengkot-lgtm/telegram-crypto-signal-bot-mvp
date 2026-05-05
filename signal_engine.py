import time
from datetime import datetime, timezone
from bitget_api import get_candles
from smc_analyzer import (
    detect_market_structure,
    detect_liquidity_sweep,
    detect_choch,
    detect_bos,
    find_ob,
    find_fvg,
    find_swing_highs,
    find_swing_lows,
    is_near_poi,
    calculate_rr,
    _c,
)
from config import MIN_RR

_CALL_DELAY = 0.3  # seconds between Bitget candle calls


def _fmt(price: float) -> str:
    if price >= 1000:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    else:
        return f"{price:.8f}"


def analyze_symbol(symbol: str, btc_4h_structure: str = "ranging") -> dict | None:
    """
    3-timeframe SMC analysis: 4H direction → 1H structure/POI → 15m confirmation.
    Only returns a result when ALL Confirmed conditions are met.
    Returns None if no signal or RR < 1.5.
    """
    try:
        candles_15m = get_candles(symbol, "15m", limit=100)
        time.sleep(_CALL_DELAY)
        candles_1h = get_candles(symbol, "1H", limit=100)
        time.sleep(_CALL_DELAY)
        candles_4h = get_candles(symbol, "4H", limit=50)
        time.sleep(_CALL_DELAY)
    except Exception as e:
        print(f"    [FETCH ERROR] {e}")
        return None

    if len(candles_15m) < 20 or len(candles_1h) < 10 or len(candles_4h) < 5:
        return None

    current_price = _c(candles_15m[-1])

    # ── 4H: Symbol direction filter ───────────────────────────────────
    struct_4h = detect_market_structure(candles_4h)
    if struct_4h == "bearish":
        return None  # only long setups; skip bearish 4H

    # ── 1H: Structure / POI ──────────────────────────────────────────
    ob_1h          = find_ob(candles_1h)
    fvg_1h         = find_fvg(candles_1h)
    bos_1h, _      = detect_bos(candles_1h)

    # ── 15m: Confirmation ────────────────────────────────────────────
    swept,   sweep_level = detect_liquidity_sweep(candles_15m)
    choch,   _           = detect_choch(candles_15m)
    bos_15m, _           = detect_bos(candles_15m)
    ob_15m  = find_ob(candles_15m)
    fvg_15m = find_fvg(candles_15m)

    # POI: prefer 15m, fall back to 1H
    active_ob  = ob_15m  or ob_1h
    active_fvg = fvg_15m or fvg_1h
    near_ob    = bool(active_ob  and is_near_poi(current_price, active_ob))
    near_fvg   = bool(active_fvg and is_near_poi(current_price, active_fvg))
    near_poi   = near_ob or near_fvg
    poi_label  = ("OB" if near_ob else "FVG") if near_poi else None
    bos_ok     = bos_15m or bos_1h

    # ── Levels ───────────────────────────────────────────────────────
    swing_highs = find_swing_highs(candles_15m)
    swing_lows  = find_swing_lows(candles_15m)

    lows_below = [l for _, l in swing_lows if l < current_price]
    if swept and sweep_level > 0 and sweep_level < current_price:
        sl_price = sweep_level * 0.998
    elif lows_below:
        sl_price = max(lows_below) * 0.998
    else:
        sl_price = current_price * 0.985

    highs_above = sorted([h for _, h in swing_highs if h > current_price])
    tp1_price = highs_above[0] if highs_above else current_price * 1.02
    tp2_price = highs_above[1] if len(highs_above) > 1 else current_price + 2 * abs(current_price - sl_price)

    rr = calculate_rr(current_price, tp1_price, sl_price)

    # ── Confirmed gate — all must pass ───────────────────────────────
    btc_ok = btc_4h_structure in ("bullish", "ranging")

    if not (swept and choch and bos_ok and near_poi and btc_ok and rr >= MIN_RR):
        return None

    # Build condition list for Telegram message
    conditions = []
    conditions.append("Liquidity sweep confirmed")
    conditions.append("15m Bullish CHOCH")
    conditions.append("15m BOS confirmed" if bos_15m else "1H BOS confirmed")
    conditions.append(f"Retesting {poi_label}")
    conditions.append(f"BTC 4H: {btc_4h_structure}")
    conditions.append(f"RR {rr:.1f}R ≥ 1.5R")

    return {
        "symbol":     symbol,
        "signal":     "confirmed",
        "direction":  "long",
        "entry":      _fmt(current_price),
        "tp1":        _fmt(tp1_price),
        "tp2":        _fmt(tp2_price),
        "sl":         _fmt(sl_price),
        "sl_raw":     sl_price,          # numeric SL for invalidation checks
        "rr":         rr,
        "conditions": conditions,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }
