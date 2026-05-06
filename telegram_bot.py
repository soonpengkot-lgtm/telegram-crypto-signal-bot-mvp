import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Telegram send failed: {e}")
        return False


def build_confirmed_message(
    symbol: str, direction: str, entry_zone: str,
    tp1: str, tp2: str, sl: str, conditions: list[str] = None
) -> str:
    pair       = symbol.replace("USDT", "/USDT")
    arrow      = "Long" if direction.lower() == "long" else "Short"
    sl_note    = "若跌破 SL" if arrow == "Long" else "若突破 SL"
    cond_lines = "\n".join(f"- {c}" for c in conditions) if conditions else (
        "- Liquidity sweep confirmed\n"
        "- 15m CHOCH\n"
        "- BOS confirmed\n"
        "- OB/FVG retest\n"
        "- BTC filter passed"
    )
    return (
        f"【{pair}｜Bitget｜SMC Confirmed ✅】\n\n"
        f"方向：{arrow}\n"
        f"Entry Zone：{entry_zone}附近\n"
        f"TP1：{tp1}\n"
        f"TP2：{tp2}\n"
        f"SL：{sl}\n\n"
        f"触发：\n"
        f"{cond_lines}\n\n"
        f"执行：\n"
        f"短线持有 30m–24h。\n"
        f"{sl_note}，signal invalidated。NFA."
    )


def build_invalidated_message(symbol: str, direction: str = "", reason: str = None) -> str:
    pair       = symbol.replace("USDT", "/USDT")
    dir_label  = f" | {direction.capitalize()}" if direction else ""
    default    = "- Hit SL 或超过 24h 未达 TP1"
    return (
        f"【{pair}{dir_label}｜Signal Invalidated ❌】\n\n"
        f"原因：\n"
        f"{reason if reason else default}\n\n"
        f"状态：\n"
        f"取消该 signal，等待下一次 setup。NFA."
    )
