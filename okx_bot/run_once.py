"""
Single-execution trading script for GitHub Actions.
Uses Multi-Signal Confluence System — scores all 50 pairs, trades the best.
"""
import os, sys, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from okx_client import OKXClient
from strategy import analyze

# ── Settings ──────────────────────────────────────────────────────────────────
LEVERAGE       = 20
CAPITAL_RATIO  = 0.95
TOP_PAIRS      = 50
MIN_SCORE      = 35    # minimum signal score to enter a trade
STATUS_FILE    = os.path.join(os.path.dirname(__file__), "..", "bot_status.json")

def load_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"logs": [], "total_trades": 0, "positions": [], "balance": 0,
                "top_signals": []}

def save_status(s):
    with open(STATUS_FILE, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def log(status, msg, level="info"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["logs"].insert(0, {"time": ts, "msg": msg, "level": level})
    status["logs"] = status["logs"][:60]
    print(f"[{ts}] {msg}")

def main():
    key    = os.environ.get("OKX_API_KEY", "").strip()
    secret = os.environ.get("OKX_API_SECRET", "").strip()
    phrase = os.environ.get("OKX_PASSPHRASE", "").strip()
    demo   = os.environ.get("OKX_IS_DEMO", "1").strip()

    if not key or not secret or not phrase:
        print("ERROR: Missing OKX credentials.")
        sys.exit(1)

    status = load_status()
    status["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["mode"]     = "Demo 🧪" if demo == "1" else "Live 💰"

    client = OKXClient(key, secret, phrase, demo)

    # Balance
    balance = client.get_balance()
    status["balance"] = round(balance, 4)
    log(status, f"الرصيد: {balance:.4f} USDT")

    # Open positions
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

    if active:
        log(status, f"صفقة مفتوحة: {', '.join(active)}")
        save_status(status)
        return

    if balance < 1:
        log(status, "الرصيد أقل من 1 USDT", "warning")
        save_status(status)
        return

    # Get top 50 pairs
    pairs = client.get_top_pairs(TOP_PAIRS)
    if not pairs:
        log(status, "فشل جلب الأزواج", "error")
        save_status(status)
        return

    log(status, f"تحليل {len(pairs)} زوج بالنظام متعدد المؤشرات...")

    # ── Score ALL pairs, pick best ────────────────────────────────────────────
    signals = []
    for inst_id in pairs:
        try:
            c15 = client.get_candles(inst_id, bar="15m", limit=200)
            c1h = client.get_candles(inst_id, bar="1H",  limit=100)
            if not c15:
                continue
            result = analyze(c15, c1h if c1h else None)
            if result["signal"]:
                signals.append({"instId": inst_id, **result})
        except Exception as e:
            continue

    # Sort by absolute score (highest conviction first)
    signals.sort(key=lambda x: abs(x["score"]), reverse=True)

    # Save top 5 signals to dashboard
    status["top_signals"] = [
        {
            "instId":  s["instId"],
            "signal":  "شراء 📈" if s["signal"] == "buy" else "بيع 📉",
            "score":   s["score"],
            "rsi":     s["details"].get("RSI_val", "—"),
            "adx":     s["details"].get("ADX", "—"),
            "vol":     s["details"].get("Vol_ratio", "—"),
        }
        for s in signals[:5]
    ]

    if not signals:
        log(status, f"لا توجد إشارات قوية (حد الدرجة: {MIN_SCORE})")
        save_status(status)
        return

    log(status, f"وُجد {len(signals)} إشارة — أفضلها: {signals[0]['instId']} (درجة: {signals[0]['score']})")

    # Trade the highest-scoring pair
    for best in signals:
        inst_id  = best["instId"]
        signal   = best["signal"]
        sl_price = best["sl_price"]
        tp_price = best["tp_price"]
        score    = best["score"]
        price    = best["price"]

        ticker = client.get_ticker(inst_id)
        if not ticker:
            continue
        live_price = float(ticker["last"])

        client.set_leverage(inst_id, LEVERAGE)
        sz = client.calculate_contracts(inst_id, balance, live_price, LEVERAGE, CAPITAL_RATIO)
        if sz <= 0:
            log(status, f"{inst_id}: حجم العقود صفر، تخطي", "warning")
            continue

        # Recalculate SL/TP from live price
        atr_val = best["atr"]
        if signal == "buy":
            sl_price = round(live_price - 1.5 * atr_val, 6)
            tp_price = round(live_price + 3.0 * atr_val, 6)
        else:
            sl_price = round(live_price + 1.5 * atr_val, 6)
            tp_price = round(live_price - 3.0 * atr_val, 6)

        result = client.place_order(inst_id, signal, sz, live_price, 0, 0,
                                    sl_override=sl_price, tp_override=tp_price)
        if result["code"] == "0":
            direction = "شراء 📈" if signal == "buy" else "بيع 📉"
            log(status,
                f"✅ {direction} {inst_id} @ {live_price} | "
                f"SL:{sl_price} TP:{tp_price} | درجة:{score}",
                "success")
            details = best["details"]
            log(status,
                f"   RSI:{details.get('RSI_val','?')} "
                f"ADX:{details.get('ADX','?')} "
                f"Vol:{details.get('Vol_ratio','?')}x "
                f"Pattern:{details.get('Pattern',0)}",
                "info")
            status["total_trades"] = status.get("total_trades", 0) + 1
            break
        else:
            log(status, f"فشل {inst_id}: {result.get('msg','')}", "error")

    save_status(status)

if __name__ == "__main__":
    main()
