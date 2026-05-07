# Candle format: [timestamp_ms, open, high, low, close, ...]

def _o(c): return float(c[1])
def _h(c): return float(c[2])
def _l(c): return float(c[3])
def _c(c): return float(c[4])


def find_swing_highs(candles: list, lookback: int = 3) -> list[tuple[int, float]]:
    result = []
    n = len(candles)
    for i in range(lookback, n - lookback):
        h = _h(candles[i])
        if all(_h(candles[i - j]) < h for j in range(1, lookback + 1)) and \
           all(_h(candles[i + j]) < h for j in range(1, lookback + 1)):
            result.append((i, h))
    return result


def find_swing_lows(candles: list, lookback: int = 3) -> list[tuple[int, float]]:
    result = []
    n = len(candles)
    for i in range(lookback, n - lookback):
        l = _l(candles[i])
        if all(_l(candles[i - j]) > l for j in range(1, lookback + 1)) and \
           all(_l(candles[i + j]) > l for j in range(1, lookback + 1)):
            result.append((i, l))
    return result


def detect_market_structure(candles: list) -> str:
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


# ── Long detections ───────────────────────────────────────────────────

def detect_liquidity_sweep(candles: list) -> tuple[bool, float]:
    """Long: wick below prior swing low, closed above it."""
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
    """Bullish CHOCH: recent close above last prior swing high."""
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
    """Bullish BOS: 2+ recent closes above a swing high level."""
    if len(candles) < 12:
        return False, 0.0
    prior_highs = find_swing_highs(candles[:-4])
    if not prior_highs:
        return False, 0.0
    for _, sh_price in reversed(prior_highs):
        if sum(1 for c in candles[-5:] if _c(c) > sh_price) >= 2:
            return True, sh_price
    return False, 0.0


def find_ob(candles: list, lookback: int = 25) -> tuple[float, float] | None:
    """Bullish OB: last bearish candle before bullish impulse closing above it."""
    start = max(0, len(candles) - lookback)
    for i in range(len(candles) - 2, start, -1):
        c, nc = candles[i], candles[i + 1]
        if _c(c) < _o(c) and _c(nc) > _o(nc) and _c(nc) > _h(c):
            return (_l(c), _h(c))
    return None


def find_fvg(candles: list, lookback: int = 20) -> tuple[float, float] | None:
    """Bullish FVG: candle[i].low > candle[i-2].high."""
    start = max(2, len(candles) - lookback)
    for i in range(len(candles) - 1, start, -1):
        gap_low, gap_high = _h(candles[i - 2]), _l(candles[i])
        if gap_high > gap_low:
            return (gap_low, gap_high)
    return None


# ── Short detections ──────────────────────────────────────────────────

def detect_liquidity_sweep_short(candles: list) -> tuple[bool, float]:
    """Short: wick above prior swing high, closed below it."""
    if len(candles) < 10:
        return False, 0.0
    prior_highs = find_swing_highs(candles[:-3])
    if not prior_highs:
        return False, 0.0
    _, sh_price = prior_highs[-1]
    for c in candles[-4:]:
        if _h(c) > sh_price and _c(c) < sh_price:
            return True, sh_price
    return False, 0.0


def detect_choch_bearish(candles: list) -> tuple[bool, float]:
    """Bearish CHOCH: recent close below last prior swing low."""
    if len(candles) < 10:
        return False, 0.0
    prior_lows = find_swing_lows(candles[:-2])
    if not prior_lows:
        return False, 0.0
    _, sl_price = prior_lows[-1]
    for c in candles[-4:]:
        if _c(c) < sl_price:
            return True, sl_price
    return False, 0.0


def detect_bos_bearish(candles: list) -> tuple[bool, float]:
    """Bearish BOS: 2+ recent closes below a swing low level."""
    if len(candles) < 12:
        return False, 0.0
    prior_lows = find_swing_lows(candles[:-4])
    if not prior_lows:
        return False, 0.0
    for _, sl_price in reversed(prior_lows):
        if sum(1 for c in candles[-5:] if _c(c) < sl_price) >= 2:
            return True, sl_price
    return False, 0.0


def find_ob_bearish(candles: list, lookback: int = 25) -> tuple[float, float] | None:
    """Bearish OB: last bullish candle before bearish impulse closing below it."""
    start = max(0, len(candles) - lookback)
    for i in range(len(candles) - 2, start, -1):
        c, nc = candles[i], candles[i + 1]
        if _c(c) > _o(c) and _c(nc) < _o(nc) and _c(nc) < _l(c):
            return (_l(c), _h(c))
    return None


def find_fvg_bearish(candles: list, lookback: int = 20) -> tuple[float, float] | None:
    """Bearish FVG: candle[i].high < candle[i-2].low."""
    start = max(2, len(candles) - lookback)
    for i in range(len(candles) - 1, start, -1):
        gap_high, gap_low = _l(candles[i - 2]), _h(candles[i])
        if gap_high > gap_low:
            return (gap_low, gap_high)
    return None


# ── Shared helpers ────────────────────────────────────────────────────

def is_near_poi(price: float, poi: tuple[float, float], threshold: float = 0.015) -> bool:
    poi_mid = (poi[0] + poi[1]) / 2
    return abs(price - poi_mid) / poi_mid <= threshold


def calculate_rr(entry: float, tp: float, sl: float) -> float:
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)


# ── RSI & divergence ──────────────────────────────────────────────────

def calculate_rsi(candles: list, period: int = 14) -> list[float]:
    closes = [_c(c) for c in candles]
    n = len(closes)
    rsi_vals = [0.0] * n

    if n < period + 1:
        return rsi_vals

    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, period + 1)]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, period + 1)]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    def _rsi(ag, al):
        return 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)

    rsi_vals[period] = _rsi(avg_gain, avg_loss)
    for i in range(period + 1, n):
        delta = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
        rsi_vals[i] = _rsi(avg_gain, avg_loss)

    return rsi_vals


def detect_rsi_bullish_divergence(
    candles: list, rsi_period: int = 14, lookback: int = 50, min_bars_apart: int = 5
) -> bool:
    """Price makes lower low but RSI makes higher low → bullish divergence."""
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    if len(recent) < rsi_period + 10:
        return False

    rsi_vals = calculate_rsi(recent, rsi_period)
    lows = [(i, p) for i, p in find_swing_lows(recent) if i >= rsi_period]

    if len(lows) < 2:
        return False

    idx1, price1 = lows[-2]
    idx2, price2 = lows[-1]

    if idx2 - idx1 < min_bars_apart:
        return False

    return price2 < price1 and rsi_vals[idx2] > rsi_vals[idx1]


def detect_rsi_bearish_divergence(
    candles: list, rsi_period: int = 14, lookback: int = 50, min_bars_apart: int = 5
) -> bool:
    """Price makes higher high but RSI makes lower high → bearish divergence."""
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    if len(recent) < rsi_period + 10:
        return False

    rsi_vals = calculate_rsi(recent, rsi_period)
    highs = [(i, p) for i, p in find_swing_highs(recent) if i >= rsi_period]

    if len(highs) < 2:
        return False

    idx1, price1 = highs[-2]
    idx2, price2 = highs[-1]

    if idx2 - idx1 < min_bars_apart:
        return False

    return price2 > price1 and rsi_vals[idx2] < rsi_vals[idx1]


# ── WaveTrend & divergence ────────────────────────────────────────────

def _ema(values: list, period: int) -> list:
    result = [0.0] * len(values)
    if not values:
        return result
    k = 2.0 / (period + 1)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = values[i] * k + result[i - 1] * (1 - k)
    return result


def calculate_wavetrend(candles: list, n1: int = 10, n2: int = 21) -> tuple:
    """WaveTrend Oscillator (LazyBear). Returns (wt1, wt2)."""
    hlc3 = [(_h(c) + _l(c) + _c(c)) / 3.0 for c in candles]
    esa  = _ema(hlc3, n1)
    d    = _ema([abs(hlc3[i] - esa[i]) for i in range(len(candles))], n1)
    ci   = [(hlc3[i] - esa[i]) / (0.015 * d[i]) if d[i] != 0 else 0.0
            for i in range(len(candles))]
    wt1  = _ema(ci, n2)
    n    = len(candles)
    wt2  = [sum(wt1[max(0, i - 3):i + 1]) / min(4, i + 1) for i in range(n)]
    return wt1, wt2


def detect_wavetrend_bullish_divergence(
    candles: list, n1: int = 10, n2: int = 21, lookback: int = 50,
    min_bars_apart: int = 5, oversold: float = -60.0
) -> bool:
    """Price lower low + WT1 higher low, both in oversold zone → bullish divergence."""
    recent  = candles[-lookback:] if len(candles) >= lookback else candles
    warmup  = n1 + n2
    if len(recent) < warmup + 5:
        return False
    wt1, _  = calculate_wavetrend(recent, n1, n2)
    lows    = [(i, p) for i, p in find_swing_lows(recent)
               if i >= warmup and wt1[i] < oversold]
    if len(lows) < 2:
        return False
    idx1, price1 = lows[-2]
    idx2, price2 = lows[-1]
    if idx2 - idx1 < min_bars_apart:
        return False
    return price2 < price1 and wt1[idx2] > wt1[idx1]


def detect_wavetrend_bearish_divergence(
    candles: list, n1: int = 10, n2: int = 21, lookback: int = 50,
    min_bars_apart: int = 5, overbought: float = 60.0
) -> bool:
    """Price higher high + WT1 lower high, both in overbought zone → bearish divergence."""
    recent  = candles[-lookback:] if len(candles) >= lookback else candles
    warmup  = n1 + n2
    if len(recent) < warmup + 5:
        return False
    wt1, _  = calculate_wavetrend(recent, n1, n2)
    highs   = [(i, p) for i, p in find_swing_highs(recent)
               if i >= warmup and wt1[i] > overbought]
    if len(highs) < 2:
        return False
    idx1, price1 = highs[-2]
    idx2, price2 = highs[-1]
    if idx2 - idx1 < min_bars_apart:
        return False
    return price2 > price1 and wt1[idx2] < wt1[idx1]
