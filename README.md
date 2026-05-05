# Telegram Crypto SMC Signal Bot — MVP

Sends SMC-based crypto signal alerts to Telegram. Price reference: **Bitget only**.  
No auto-trading. No financial advice.

---

## Setup

```powershell
# 1. Copy env file
copy .env.example .env
# Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

---

## Signal Types

| Signal | Meaning |
|--------|---------|
| SMC Watch 🟡 | Setup forming, waiting for confirmation |
| SMC Confirmed ✅ | All conditions met: sweep + CHOCH + BOS + retest + RR ≥ 1.5R |
| Invalidated ❌ | Price broke SL / BTC reversed / signal expired after 24h |

---

## Watchlist

**Core:** BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT  
**Alt:** ADAUSDT, DOGEUSDT, PEPEUSDT

---

## Strategy Logic (SMC)

1. 4H — Main direction filter
2. 1H — Structure / POI identification
3. 15m — Entry confirmation (CHOCH, BOS, OB/FVG retest)
4. BTC direction filter (must not be reversing strongly)
5. RR ≥ 1.5 required for Confirmed signal

---

## Roadmap

- [x] Phase 1: Project scaffold + sample Telegram messages
- [ ] Phase 2: Live Bitget price feed (REST API)
- [ ] Phase 3: Basic CHOCH/BOS/structure detection
- [ ] Phase 4: Cooldown logic (Watch: 2h, Confirmed: 4h per symbol)
- [ ] Phase 5: Scheduler (every 15 minutes via GitHub Actions or cron)

---

**NFA. For educational and personal use only.**
