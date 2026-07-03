import threading
import time
import json
import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, session

from okx_client import OKXClient
from strategy import get_signal
import config as cfg

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Bot state
bot_state = {
    "running": False,
    "balance": 0.0,
    "positions": [],
    "logs": [],
    "total_trades": 0,
    "winning_trades": 0,
    "api_configured": False,
    "thread": None,
}

credentials = {
    "api_key": cfg.API_KEY,
    "api_secret": cfg.API_SECRET,
    "passphrase": cfg.PASSPHRASE,
    "is_demo": cfg.IS_DEMO,
}


def add_log(msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    bot_state["logs"].insert(0, {"time": ts, "msg": msg, "level": level})
    if len(bot_state["logs"]) > 100:
        bot_state["logs"] = bot_state["logs"][:100]


def bot_loop():
    client = OKXClient(
        credentials["api_key"],
        credentials["api_secret"],
        credentials["passphrase"],
        credentials["is_demo"]
    )
    add_log("البوت يعمل ✅", "success")

    scan = 0
    while bot_state["running"]:
        try:
            scan += 1
            add_log(f"فحص #{scan} — جارٍ تحليل السوق...", "info")

            balance = client.get_balance()
            bot_state["balance"] = balance

            positions = client.get_all_positions()
            bot_state["positions"] = positions
            active = {p["instId"] for p in positions}

            if len(active) >= cfg.MAX_POSITIONS:
                add_log(f"صفقة مفتوحة: {', '.join(active)}", "info")
                time.sleep(cfg.SCAN_INTERVAL)
                continue

            if balance < 1:
                add_log("الرصيد أقل من 1 USDT", "warning")
                time.sleep(cfg.SCAN_INTERVAL)
                continue

            pairs = client.get_top_pairs(cfg.TOP_PAIRS_COUNT)
            if not pairs:
                add_log("فشل جلب الأزواج", "error")
                time.sleep(cfg.SCAN_INTERVAL)
                continue

            found = False
            for inst_id in pairs:
                if inst_id in active:
                    continue
                candles = client.get_candles(inst_id, bar=cfg.TIMEFRAME, limit=60)
                if not candles:
                    continue
                signal = get_signal(candles,
                    ema_fast=cfg.EMA_FAST, ema_slow=cfg.EMA_SLOW,
                    rsi_period=cfg.RSI_PERIOD,
                    rsi_buy_max=cfg.RSI_BUY_MAX, rsi_sell_min=cfg.RSI_SELL_MIN)
                if not signal:
                    continue
                ticker = client.get_ticker(inst_id)
                if not ticker:
                    continue
                price = float(ticker["last"])
                client.set_leverage(inst_id, cfg.LEVERAGE)
                sz = client.calculate_contracts(inst_id, balance, price, cfg.LEVERAGE, cfg.CAPITAL_RATIO)
                if sz <= 0:
                    continue
                result = client.place_order(inst_id, signal, sz, price, cfg.STOP_LOSS_PCT, cfg.TAKE_PROFIT_PCT)
                if result["code"] == "0":
                    direction = "شراء 📈" if signal == "buy" else "بيع 📉"
                    add_log(f"✅ {direction} {inst_id} @ {price}", "success")
                    bot_state["total_trades"] += 1
                    found = True
                    break
                else:
                    add_log(f"فشل {inst_id}: {result.get('msg','')}", "error")

            if not found:
                add_log("لا توجد إشارات حالياً", "info")

            time.sleep(cfg.SCAN_INTERVAL)

        except Exception as e:
            add_log(f"خطأ: {str(e)}", "error")
            time.sleep(30)

    add_log("البوت توقف ⛔", "warning")


@app.route("/")
def index():
    return render_template("index.html",
        is_demo=credentials["is_demo"] == "1",
        leverage=cfg.LEVERAGE,
        sl=cfg.STOP_LOSS_PCT * 100,
        tp=cfg.TAKE_PROFIT_PCT * 100,
        configured=bool(credentials["api_key"])
    )


@app.route("/api/status")
def status():
    return jsonify({
        "running": bot_state["running"],
        "balance": round(bot_state["balance"], 4),
        "positions": len(bot_state["positions"]),
        "positions_data": bot_state["positions"],
        "logs": bot_state["logs"][:20],
        "total_trades": bot_state["total_trades"],
        "configured": bool(credentials["api_key"]),
    })


@app.route("/api/start", methods=["POST"])
def start():
    if not credentials["api_key"]:
        return jsonify({"ok": False, "msg": "أدخل بيانات API أولاً"})
    if bot_state["running"]:
        return jsonify({"ok": False, "msg": "البوت يعمل بالفعل"})
    bot_state["running"] = True
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    bot_state["thread"] = t
    return jsonify({"ok": True})


@app.route("/api/stop", methods=["POST"])
def stop():
    bot_state["running"] = False
    return jsonify({"ok": True})


@app.route("/api/configure", methods=["POST"])
def configure():
    data = request.json
    credentials["api_key"] = data.get("api_key", "").strip()
    credentials["api_secret"] = data.get("api_secret", "").strip()
    credentials["passphrase"] = data.get("passphrase", "").strip()
    credentials["is_demo"] = data.get("is_demo", "1")
    add_log("تم حفظ بيانات API ✅", "success")
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
