import time
import requests

BITGET_BASE  = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"

GRANULARITY = {
    "15m": "15min",
    "1H":  "1H",
    "4H":  "4H",
}


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "00000":
        raise ValueError(f"Bitget API error: {data.get('msg')} | url={url}")
    return data


def get_candles(symbol: str, granularity: str = "15m", limit: int = 100) -> list:
    """
    Returns OHLCV candles sorted oldest→newest.
    Each candle: [timestamp_ms, open, high, low, close, baseVol, quoteVol]
    """
    url = f"{BITGET_BASE}/api/v2/mix/market/candles"
    params = {
        "symbol":      symbol,
        "productType": PRODUCT_TYPE,
        "granularity": GRANULARITY.get(granularity, granularity),
        "limit":       limit,
    }
    data = _get(url, params)
    candles = data["data"]
    return sorted(candles, key=lambda c: int(c[0]))  # ascending by timestamp


def get_ticker(symbol: str) -> dict:
    url = f"{BITGET_BASE}/api/v2/mix/market/ticker"
    data = _get(url, {"symbol": symbol, "productType": PRODUCT_TYPE})
    return data["data"][0]


def get_current_price(symbol: str) -> float:
    return float(get_ticker(symbol)["lastPr"])


def scan_prices(symbols: list[str]) -> dict:
    """Fetch ticker for all symbols. Returns {symbol: {price, change24, high24, low24}}."""
    results = {}
    for sym in symbols:
        try:
            t = get_ticker(sym)
            results[sym] = {
                "price":    float(t["lastPr"]),
                "change24": float(t.get("change24H", 0)) * 100,
                "high24":   float(t["high24H"]),
                "low24":    float(t["low24H"]),
            }
        except Exception as e:
            print(f"  [WARN] {sym} ticker failed: {e}")
            results[sym] = None
        time.sleep(0.2)
    return results
