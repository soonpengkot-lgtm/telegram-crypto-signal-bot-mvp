# Candle format from CoinGecko OHLC: [timestamp_ms, open, high, low, close]

def _o(c): return float(c[1])
def _h(c): return float(c[2])
def _l(c): return float(c[3])
def _c(c): return float(c[4])


def find_swing_highs(candles: list, lookback: int = 3) -> list[tuple[int, float]]:
    """Swing high: candle whose high > N candles on each side."""
    result = []
    n = len(candles)
    for i in range(lookback, n - lookback):
        h = _h(candles[i])
        if all(_h(candles[i - j]) < h for j in range(1, lookback + 1)) and \
           all(_h(candles[i + j]) < h for j in range(1, lookback + 1)):
            result.append((i, h))
    return result


def find_swing_lows(candles: list, lookback: int = 3) -> list[tuple[int, float]]:
    """Swing low: candle whose low < N candles on each side."""
    result = []
    n = len(candles)
    for i in range(lookback, n - lookback):
        l = _l(candles[i])
        if all(_l(candles[i - j]) > l for j in range(1, lookback + 1)) and \
           all(_l(candles[i + j]) > l for j in range(1, lookback + 1)):
            result.append((i, l))
    return result


def detect_market_structure(candles: list) -> str:
    """Returns 'bullish', 'bearish', or 'ranging' from swing structure."""
    highs = find_swing_highs(candles)
    lows  = find_swing_lows(candles)
    if len(highs) < 2 or len(lows) < 2:
        return "ranging"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1]  > lows[-2][1]
    lh = highs[-1][1] < highs[-2][1]
    ll = lows[-1][1]  < lows[-2][1]
    if hh and hl:
        return "bullish"
    if lh and ll:
        return "bearish"
    return "ranging"


def detect_liquidity_sweep(candles: list) -> tuple[bool, float]:
    """
    Long setup: recent candle wicked below a prior swing low, closed above it.
    Returns (swept, sweep_level).
    """
    if len(candles) < 10:
        return False, 0.0
    prior_lows = find_swing_lows(candles[:-3])
    if not prior_lows:
        return False, 0.0
    _, sl_price = prior_lows[-1]
    for c in candles[-4:]:
        if _l(c) < sl_price and _c(c) > sl_price:
            return True, sl_price
    return False, 0.0


def detect_choch(candles: list) -> tuple[bool, float]:
    """
    Bullish CHOCH: a recent candle closes above the last prior swing high.
    Returns (detected, choch_level).
    """
    if len(candles) < 10:
        return False, 0.0
    prior_highs = find_swing_highs(candles[:-2])
    if not prior_highs:
        return False, 0.0
    _, sh_price = prior_highs[-1]
    for c in candles[-4:]:
        if _c(c) > sh_price:
            return True, sh_price
    return False, 0.0


def detect_bos(candles: list) -> tuple[bool, float]:
    """
    Bullish BOS: at least 2 recent closes above a swing high level (structure confirmed).
    Returns (detected, bos_level).
    """
    if len(candles) < 12:
        return False, 0.0
    prior_highs = find_swing_highs(candles[:-4])
    if not prior_highs:
        return False, 0.0
    for _, sh_price in reversed(prior_highs):
        closes_above = sum(1 for c in candles[-5:] if _c(c) > sh_price)
        if closes_above >= 2:
            return True, sh_price
    return False, 0.0


def find_ob(candles: list, lookback: int = 25) -> tuple[float, float] | None:
    """
    Bullish OB: last bearish candle before a bullish impulse that closes above it.
    Returns (ob_low, ob_high) or None.
    """
    start = max(0, len(candles) - lookback)
    for i in range(len(candles) - 2, start, -1):
        c      = candles[i]
        next_c = candles[i + 1]
        if _c(c) < _o(c) and _c(next_c) > _o(next_c) and _c(next_c) > _h(c):
            return (_l(c), _h(c))
    return None


def find_fvg(candles: list, lookback: int = 20) -> tuple[float, float] | None:
    """
    Bullish FVG: gap where candle[i].low > candle[i-2].high.
    Scans most recent candles first.
    Returns (fvg_low, fvg_high) or None.
    """
    start = max(2, len(candles) - lookback)
    for i in range(len(candles) - 1, start, -1):
        gap_low  = _h(candles[i - 2])
        gap_high = _l(candles[i])
        if gap_high > gap_low:
            return (gap_low, gap_high)
    return None


def is_near_poi(price: float, poi: tuple[float, float], threshold: float = 0.015) -> bool:
    """Price is within threshold% of the POI midpoint."""
    poi_mid = (poi[0] + poi[1]) / 2
    return abs(price - poi_mid) / poi_mid <= threshold


def calculate_rr(entry: float, tp: float, sl: float) -> float:
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)
