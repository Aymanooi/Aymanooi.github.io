"""
Single execution script for GitHub Actions.
Reads credentials from environment variables, checks signals, places trades,
and writes status to bot_status.json at the repo root.
"""
import os
import sys
import json
import math
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from okx_client import OKXClient
from strategy import get_signal

# Settings
LEVERAGE       = 20
CAPITAL_RATIO  = 0.95
STOP_LOSS_PCT  = 0.02
TAKE_PROFIT_PCT= 0.04
EMA_FAST       = 9
EMA_SLOW       = 21
RSI_PERIOD     = 14
RSI_BUY_MAX    = 65
RSI_SELL_MIN   = 35
TIMEFRAME      = "15m"
TOP_PAIRS      = 50

STATUS_FILE = os.path.join(os.path.dirname(__file__), "..", "bot_status.json")

def load_status():
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"logs": [], "total_trades": 0, "positions": [], "balance": 0}

def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def log_event(status, msg, level="info"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["logs"].insert(0, {"time": ts, "msg": msg, "level": level})
    status["logs"] = status["logs"][:50]
    print(f"[{ts}] {msg}")

def main():
    api_key    = os.environ.get("OKX_API_KEY", "").strip()
    api_secret = os.environ.get("OKX_API_SECRET", "").strip()
    passphrase = os.environ.get("OKX_PASSPHRASE", "").strip()
    is_demo    = os.environ.get("OKX_IS_DEMO", "1").strip()

    if not api_key or not api_secret or not passphrase:
        print("ERROR: Missing OKX credentials in environment variables.")
        sys.exit(1)

    status = load_status()
    status["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["mode"]     = "Demo 🧪" if is_demo == "1" else "Live 💰"

    client = OKXClient(api_key, api_secret, passphrase, is_demo)

    # Balance
    balance = client.get_balance()
    status["balance"] = round(balance, 4)
    log_event(status, f"الرصيد: {balance:.4f} USDT")

    # Positions
    positions = client.get_all_positions()
    status["positions"] = [
        {
            "instId": p.get("instId"),
            "side":   "شراء 📈" if float(p.get("pos", 0)) > 0 else "بيع 📉",
            "size":   abs(float(p.get("pos", 0))),
            "entry":  float(p.get("avgPx", 0)),
            "pnl":    round(float(p.get("upl", 0)), 4),
        }
        for p in positions if float(p.get("pos", 0)) != 0
    ]
    active = {p["instId"] for p in positions if float(p.get("pos", 0)) != 0}

    if len(active) >= 1:
        log_event(status, f"صفقة مفتوحة: {', '.join(active)} — لا حاجة للدخول")
        save_status(status)
        return

    if balance < 1:
        log_event(status, "الرصيد أقل من 1 USDT", "warning")
        save_status(status)
        return

    # Scan pairs
    pairs = client.get_top_pairs(TOP_PAIRS)
    if not pairs:
        log_event(status, "فشل جلب الأزواج", "error")
        save_status(status)
        return

    log_event(status, f"تحليل {len(pairs)} زوج...")

    for inst_id in pairs:
        candles = client.get_candles(inst_id, bar=TIMEFRAME, limit=60)
        if not candles:
            continue

        signal = get_signal(candles,
            ema_fast=EMA_FAST, ema_slow=EMA_SLOW,
            rsi_period=RSI_PERIOD,
            rsi_buy_max=RSI_BUY_MAX, rsi_sell_min=RSI_SELL_MIN)

        if not signal:
            continue

        ticker = client.get_ticker(inst_id)
        if not ticker:
            continue
        price = float(ticker["last"])

        client.set_leverage(inst_id, LEVERAGE)
        sz = client.calculate_contracts(inst_id, balance, price, LEVERAGE, CAPITAL_RATIO)
        if sz <= 0:
            continue

        result = client.place_order(inst_id, signal, sz, price, STOP_LOSS_PCT, TAKE_PROFIT_PCT)
        if result["code"] == "0":
            direction = "شراء 📈" if signal == "buy" else "بيع 📉"
            sl = price * (1 - STOP_LOSS_PCT) if signal == "buy" else price * (1 + STOP_LOSS_PCT)
            tp = price * (1 + TAKE_PROFIT_PCT) if signal == "buy" else price * (1 - TAKE_PROFIT_PCT)
            log_event(status, f"✅ {direction} {inst_id} @ {price:.4f} | SL:{sl:.4f} TP:{tp:.4f}", "success")
            status["total_trades"] = status.get("total_trades", 0) + 1
            break
        else:
            log_event(status, f"فشل {inst_id}: {result.get('msg','')}", "error")
    else:
        log_event(status, "لا توجد إشارات في هذا الفحص")

    save_status(status)

if __name__ == "__main__":
    main()
