import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")
        return False


def build_watch_message(symbol: str, direction: str, entry_ref: str, tp1: str, tp2: str, sl: str) -> str:
    pair = symbol.replace("USDT", "/USDT")
    arrow = "Long" if direction.lower() == "long" else "Short"
    return (
        f"【{pair}｜Bitget｜SMC Watch 🟡】\n\n"
        f"方向：{arrow} Watch\n"
        f"状态：等待确认\n\n"
        f"Entry Ref：{entry_ref}\n"
        f"TP：{tp1} / {tp2}\n"
        f"SL：{sl}\n\n"
        f"确认条件：\n"
        f"- Sweep liquidity 后收回\n"
        f"- 15m Bullish CHOCH\n"
        f"- 15m / 1H BOS confirmed\n"
        f"- Retest OB/FVG 不破\n"
        f"- BTC 不走弱\n\n"
        f"RR：\n"
        f"至少 1.5R 才触发正式 signal。\n\n"
        f"结论：\n"
        f"条件未齐 = Watch only，不直接进场。NFA."
    )


def build_confirmed_message(symbol: str, direction: str, entry_zone: str, tp1: str, tp2: str, sl: str) -> str:
    pair = symbol.replace("USDT", "/USDT")
    arrow = "Long" if direction.lower() == "long" else "Short"
    return (
        f"【{pair}｜Bitget｜SMC Confirmed ✅】\n\n"
        f"方向：{arrow}\n"
        f"Entry Zone：{entry_zone}附近\n"
        f"TP1：{tp1}\n"
        f"TP2：{tp2}\n"
        f"SL：{sl}\n\n"
        f"触发：\n"
        f"- Liquidity sweep confirmed\n"
        f"- 15m Bullish CHOCH\n"
        f"- 1H BOS confirmed\n"
        f"- OB/FVG retest holding\n"
        f"- BTC stable\n\n"
        f"执行：\n"
        f"短线持有 30m–24h。\n"
        f"若跌破 SL，signal invalidated。NFA."
    )


def build_invalidated_message(symbol: str, reason: str = None) -> str:
    pair = symbol.replace("USDT", "/USDT")
    default_reason = (
        "- 跌破 invalidation level\n"
        "- 或 BTC 反向波动\n"
        "- 或超过 24h 未确认"
    )
    return (
        f"【{pair}｜Signal Invalidated ❌】\n\n"
        f"原因：\n"
        f"{reason if reason else default_reason}\n\n"
        f"状态：\n"
        f"取消该 signal，等待下一次 setup。NFA."
    )
