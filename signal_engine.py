import time
from datetime import datetime, timezone
from bitget_api import get_candles
from smc_analyzer import (
    detect_market_structure,
    detect_liquidity_sweep, detect_choch,
    find_ob, find_fvg,
    detect_liquidity_sweep_short, detect_choch_bearish,
    find_ob_bearish, find_fvg_bearish,
    find_swing_highs, find_swing_lows,
    is_near_poi, calculate_rr, _c,
    detect_wavetrend_bullish_divergence, detect_wavetrend_bearish_divergence,
)
from config import RR_THRESHOLDS

_CALL_DELAY = 0.3


def _fmt(price: float) -> str:
    if price >= 1000:   return f"{price:,.2f}"
    elif price >= 1:    return f"{price:.4f}"
    else:               return f"{price:.8f}"


def _min_rr(symbol: str) -> float:
    return RR_THRESHOLDS.get(symbol, 1.5)


def _btc_filter_long(symbol: str, btc_structures: dict) -> bool:
    """Long allowed unless BTC 15m or 1H is bearish (for alts). BTC itself uses 4H only."""
    if symbol == "BTCUSDT":
        return btc_structures.get("4H", "ranging") != "bearish"
    return (
        btc_structures.get("15m", "ranging") != "bearish" and
        btc_structures.get("1H",  "ranging") != "bearish"
    )


def _btc_filter_short(symbol: str, btc_structures: dict) -> bool:
    """Short allowed unless BTC 15m or 1H is bullish (for alts). BTC itself uses 4H only."""
    if symbol == "BTCUSDT":
        return btc_structures.get("4H", "ranging") != "bullish"
    return (
        btc_structures.get("15m", "ranging") != "bullish" and
        btc_structures.get("1H",  "ranging") != "bullish"
    )


def _build_long(symbol, candles_15m, candles_1h, candles_4h, btc_structures) -> dict | None:
    struct_4h = detect_market_structure(candles_4h)
    if struct_4h == "bearish":
        return None
    if not _btc_filter_long(symbol, btc_structures):
        return None

    current = _c(candles_15m[-1])

    swept, sweep_lvl = detect_liquidity_sweep(candles_15m)
    choch, _         = detect_choch(candles_15m)
    rsi_div          = detect_wavetrend_bullish_divergence(candles_15m)
    ob_15m, fvg_15m  = find_ob(candles_15m), find_fvg(candles_15m)
    ob_1h,  fvg_1h   = find_ob(candles_1h),  find_fvg(candles_1h)

    active_ob  = ob_15m  or ob_1h
    active_fvg = fvg_15m or fvg_1h
    near_ob    = bool(active_ob  and is_near_poi(current, active_ob))
    near_fvg   = bool(active_fvg and is_near_poi(current, active_fvg))
    near_poi   = near_ob or near_fvg
    poi_label  = ("OB" if near_ob else "FVG") if near_poi else None

    swing_highs = find_swing_highs(candles_15m)
    swing_lows  = find_swing_lows(candles_15m)

    lows_below = [l for _, l in swing_lows if l < current]
    if swept and sweep_lvl > 0 and sweep_lvl < current:
        sl_raw = sweep_lvl * 0.998
    elif lows_below:
        sl_raw = max(lows_below) * 0.998
    else:
        sl_raw = current * 0.985

    highs_above = sorted([h for _, h in swing_highs if h > current])
    tp1_raw = highs_above[0] if highs_above else current * 1.02
    tp2_raw = highs_above[1] if len(highs_above) > 1 else current + 2 * abs(current - sl_raw)

    rr      = calculate_rr(current, tp1_raw, sl_raw)
    min_rr  = _min_rr(symbol)

    if not (swept and choch and rsi_div and near_poi and rr >= min_rr):
        return None

    conditions = [
        "Sweep lower liquidity confirmed",
        "15m Bullish CHOCH",
        "WaveTrend bullish divergence (15m)",
        f"Retesting {poi_label} (holding)",
        f"BTC filter passed",
        f"RR {rr:.1f}R ≥ {min_rr}R",
    ]

    return {
        "symbol":     symbol,
        "signal":     "confirmed",
        "direction":  "long",
        "entry":      _fmt(current),
        "tp1":        _fmt(tp1_raw),
        "tp2":        _fmt(tp2_raw),
        "sl":         _fmt(sl_raw),
        "sl_raw":     sl_raw,
        "tp1_raw":    tp1_raw,
        "rr":         rr,
        "conditions": conditions,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


def _build_short(symbol, candles_15m, candles_1h, candles_4h, btc_structures) -> dict | None:
    struct_4h = detect_market_structure(candles_4h)
    if struct_4h == "bullish":
        return None
    if not _btc_filter_short(symbol, btc_structures):
        return None

    current = _c(candles_15m[-1])

    swept, sweep_lvl  = detect_liquidity_sweep_short(candles_15m)
    choch, _          = detect_choch_bearish(candles_15m)
    rsi_div           = detect_wavetrend_bearish_divergence(candles_15m)
    ob_15m, fvg_15m   = find_ob_bearish(candles_15m), find_fvg_bearish(candles_15m)
    ob_1h,  fvg_1h    = find_ob_bearish(candles_1h),  find_fvg_bearish(candles_1h)

    active_ob  = ob_15m  or ob_1h
    active_fvg = fvg_15m or fvg_1h
    near_ob    = bool(active_ob  and is_near_poi(current, active_ob))
    near_fvg   = bool(active_fvg and is_near_poi(current, active_fvg))
    near_poi   = near_ob or near_fvg
    poi_label  = ("OB" if near_ob else "FVG") if near_poi else None

    swing_highs = find_swing_highs(candles_15m)
    swing_lows  = find_swing_lows(candles_15m)

    highs_above = [h for _, h in swing_highs if h > current]
    if swept and sweep_lvl > current:
        sl_raw = sweep_lvl * 1.002
    elif highs_above:
        sl_raw = min(highs_above) * 1.002
    else:
        sl_raw = current * 1.015

    lows_below = sorted([l for _, l in swing_lows if l < current], reverse=True)
    tp1_raw = lows_below[0] if lows_below else current * 0.98
    tp2_raw = lows_below[1] if len(lows_below) > 1 else current - 2 * abs(sl_raw - current)

    rr      = calculate_rr(current, tp1_raw, sl_raw)
    min_rr  = _min_rr(symbol)

    if not (swept and choch and rsi_div and near_poi and rr >= min_rr):
        return None

    conditions = [
        "Sweep upper liquidity confirmed",
        "15m Bearish CHOCH",
        "WaveTrend bearish divergence (15m)",
        f"Retesting {poi_label} (rejected)",
        f"BTC filter passed",
        f"RR {rr:.1f}R ≥ {min_rr}R",
    ]

    return {
        "symbol":     symbol,
        "signal":     "confirmed",
        "direction":  "short",
        "entry":      _fmt(current),
        "tp1":        _fmt(tp1_raw),
        "tp2":        _fmt(tp2_raw),
        "sl":         _fmt(sl_raw),
        "sl_raw":     sl_raw,
        "tp1_raw":    tp1_raw,
        "rr":         rr,
        "conditions": conditions,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }


def analyze_symbol(symbol: str, btc_structures: dict) -> list[dict]:
    """
    Returns list of confirmed signals for a symbol (Long and/or Short).
    Fetches candles once and checks both directions.
    """
    try:
        candles_15m = get_candles(symbol, "15m", limit=100)
        time.sleep(_CALL_DELAY)
        candles_1h  = get_candles(symbol, "1H",  limit=100)
        time.sleep(_CALL_DELAY)
        candles_4h  = get_candles(symbol, "4H",  limit=50)
        time.sleep(_CALL_DELAY)
    except Exception as e:
        print(f"    [FETCH ERROR] {e}")
        return []

    if len(candles_15m) < 20 or len(candles_1h) < 10 or len(candles_4h) < 5:
        return []

    results = []
    long_sig  = _build_long(symbol,  candles_15m, candles_1h, candles_4h, btc_structures)
    short_sig = _build_short(symbol, candles_15m, candles_1h, candles_4h, btc_structures)
    if long_sig:
        results.append(long_sig)
    if short_sig:
        results.append(short_sig)
    return results
