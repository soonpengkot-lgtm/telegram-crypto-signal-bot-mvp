import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_API_KEY = os.getenv("COINGECKO_API_KEY", "")  # optional free demo key

# Bitget symbol → CoinGecko coin ID
SYMBOL_MAP = {
    "BTCUSDT":  "bitcoin",
    "ETHUSDT":  "ethereum",
    "SOLUSDT":  "solana",
    "XRPUSDT":  "ripple",
    "ADAUSDT":  "cardano",
    "DOGEUSDT": "dogecoin",
    "PEPEUSDT": "pepe",
}


def _get_coin_id(symbol: str) -> str:
    coin_id = SYMBOL_MAP.get(symbol.upper())
    if not coin_id:
        raise ValueError(f"No CoinGecko mapping for symbol: {symbol}")
    return coin_id


def _get(url: str, params: dict, max_retries: int = 4) -> requests.Response:
    """GET with retry on 429. Backs off 30s per attempt."""
    if _API_KEY:
        params = {**params, "x_cg_demo_api_key": _API_KEY}
    for attempt in range(max_retries):
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  [Rate limit] waiting {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Max retries exceeded for {url}")


def get_markets(symbols: list[str]) -> dict:
    """Fetch price + 24h stats for all symbols in one call."""
    ids = ",".join(_get_coin_id(s) for s in symbols)
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {"vs_currency": "usd", "ids": ids, "price_change_percentage": "24h"}
    resp = _get(url, params)
    id_to_symbol = {v: k for k, v in SYMBOL_MAP.items()}
    results = {}
    for coin in resp.json():
        sym = id_to_symbol.get(coin["id"])
        if sym:
            results[sym] = {
                "price":    coin["current_price"],
                "change24": coin.get("price_change_percentage_24h") or 0.0,
                "high24":   coin.get("high_24h") or 0.0,
                "low24":    coin.get("low_24h") or 0.0,
            }
    return results


def get_current_price(symbol: str) -> float:
    return get_markets([symbol])[symbol]["price"]


def get_ohlcv(symbol: str, days: int = 1) -> list:
    """
    Fetch OHLCV candles from CoinGecko OHLC endpoint.
    days=1 → ~30min candles (~48 points)
    days=7 → ~4H candles  (~42 points)
    Returns: [[timestamp_ms, open, high, low, close], ...]
    """
    coin_id = _get_coin_id(symbol)
    url = f"{COINGECKO_BASE}/coins/{coin_id}/ohlc"
    resp = _get(url, {"vs_currency": "usd", "days": days})
    return resp.json()


def scan_watchlist(symbols: list[str]) -> dict:
    try:
        return get_markets(symbols)
    except Exception as e:
        print(f"  [ERROR] CoinGecko scan failed: {e}")
        return {s: None for s in symbols}
