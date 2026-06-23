"""
run_once.py — GitHub Actions entry point
Runs ONE cycle of the Snowball v22 bot, saves status + brain memory.
"""
import asyncio
import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

# ── Brain (adaptive learning) ─────────────────────────────────────────────────
import brain

STATUS_FILE = os.path.join(os.path.dirname(__file__), "..", "bot_status.json")
DB_FILE     = os.path.join(os.path.dirname(__file__), "snowball_v19.db")

def load_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"logs": [], "total_trades": 0, "positions": [], "balance": 0}

def save_status(s):
    with open(STATUS_FILE, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def add_log(status, msg, level="info"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["logs"].insert(0, {"time": ts, "msg": msg, "level": level})
    status["logs"] = status["logs"][:80]
    print(f"[{ts}] {msg}")


async def run():
    # ── Validate credentials ──────────────────────────────────────────────────
    key    = os.environ.get("OKX_API_KEY", "").strip()
    secret = os.environ.get("OKX_API_SECRET", os.environ.get("OKX_SECRET_KEY","")).strip()
    phrase = os.environ.get("OKX_PASSPHRASE", "").strip()
    demo   = os.environ.get("OKX_IS_DEMO", "1").strip()

    if not key or not secret or not phrase:
        print("❌ Missing OKX credentials in GitHub Secrets.")
        sys.exit(1)

    # Set env vars so FinalConfig picks them up
    os.environ["OKX_API_KEY"]    = key
    os.environ["OKX_API_SECRET"] = secret
    os.environ["OKX_SECRET_KEY"] = secret
    os.environ["OKX_PASSPHRASE"] = phrase
    os.environ["OKX_IS_DEMO"]    = demo

    status = load_status()
    status["last_run"]  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["mode"]      = "Demo 🧪" if demo != "0" else "Live 💰"
    status["risk_mode"] = os.environ.get("RISK_MODE", "safe").strip().lower()

    memory = brain.load_memory()

    add_log(status, "🚀 تشغيل Snowball v22 + Brain...", "success")
    add_log(status, f"الوضع: {status['mode']}", "info")

    # Go directly to MSCS — Snowball v22 module is not available in this environment
    await _fallback_mscs(status, memory, key, secret, phrase, demo)

    brain.save_memory(memory)
    save_status(status)
    print("✅ Done.")


async def _fallback_mscs(status, memory, key, secret, phrase, demo):
    """Fallback to MSCS strategy if Snowball fails."""
    from okx_client import OKXClient
    from strategy import analyze
    import config as cfg

    LEVERAGE        = cfg.LEVERAGE
    STOP_LOSS_PCT   = 0.02
    TAKE_PROFIT_PCT = 0.04
    CAPITAL_RATIO   = 0.95
    TOP_PAIRS       = 50

    add_log(status, f"⚙️ وضع المخاطرة: {cfg.RISK_MODE} | رافعة: x{LEVERAGE}", "info")

    client = OKXClient(key, secret, phrase, demo)
    balance = client.get_balance()
    status["balance"] = round(balance, 4)
    add_log(status, f"💰 الرصيد: ${balance:.4f} USDT")

    positions = client.get_all_positions()
    active    = {p["instId"] for p in positions if float(p.get("pos", 0)) != 0}
    status["positions"] = [
        {"instId": p["instId"],
         "side":   "شراء 📈" if float(p.get("pos",0))>0 else "بيع 📉",
         "entry":  float(p.get("avgPx",0)),
         "size":   abs(float(p.get("pos",0))),
         "pnl":    round(float(p.get("upl",0)),4)}
        for p in positions if float(p.get("pos",0)) != 0
    ]

    # Detect positions closed since last run → start cooldown so we don't re-enter
    prev_open    = {p["instId"] for p in status.get("positions", [])}
    newly_closed = prev_open - active
    if newly_closed:
        for closed_id in newly_closed:
            brain.mark_exited(memory, closed_id)
        add_log(status,
            f"⏳ أُغلقت: {', '.join(newly_closed)} — "
            f"محظورة من الدخول {brain.COOLDOWN_HOURS} ساعات", "info")

    # كم مركزاً يمكن فتحه الآن؟
    slots_available = cfg.MAX_POSITIONS - len(active)
    if slots_available <= 0 or balance < 1:
        add_log(status, f"مراكز مفتوحة: {len(active)}/{cfg.MAX_POSITIONS} — لا دخول جديد")
        return

    pairs   = client.get_top_pairs(TOP_PAIRS)
    signals = []
    skipped_losers  = 0
    skipped_cooldown = 0
    for inst_id in pairs:
        # تجاهل الأزواج المفتوحة بالفعل
        if inst_id in active:
            continue
        # تجاهل العملات التي أُغلقت مؤخراً (فترة التهدئة)
        if not brain.can_reenter(memory, inst_id):
            skipped_cooldown += 1
            continue
        try:
            # nitro/hyper mode: skip symbols proven to be losing
            if cfg.FILTER_LOSERS and not brain.should_trade_symbol(memory, inst_id):
                skipped_losers += 1
                continue
            c15 = client.get_candles(inst_id, bar="15m", limit=60)
            c1h = client.get_candles(inst_id, bar="1H", limit=60)
            r   = analyze(c15, c1h)
            if r["signal"]:
                adj, prob = brain.adjusted_score(r["details"], memory)
                signals.append({"instId": inst_id, **r,
                                 "adj_score": adj, "prob": prob})
        except Exception:
            continue
    if skipped_cooldown:
        add_log(status, f"⏳ تخطّى {skipped_cooldown} عملة في فترة التهدئة ({brain.COOLDOWN_HOURS}ساعة)", "info")
    if skipped_losers:
        add_log(status, f"🚫 تخطّى {skipped_losers} عملة خاسرة (فلتر Nitro/Hyper)", "info")

    signals.sort(key=lambda x: abs(x.get("adj_score", x["score"])), reverse=True)
    status["top_signals"] = [
        {"instId": s["instId"], "signal": s["signal"],
         "score": s["score"], "prob": round(s.get("prob",0.5),2)}
        for s in signals[:5]
    ]

    if not signals:
        add_log(status, "لا توجد إشارات كافية")
        return

    # رأس المال الكامل مقسّماً على عدد المراكز المتزامنة
    risk_capital = balance / max(cfg.MAX_POSITIONS, 1)

    trades_entered = 0
    # Iterate through ALL ranked signals until slots are filled
    for best in signals:
        if trades_entered >= slots_available:
            break

        inst_id  = best["instId"]
        signal   = best["signal"]
        score    = best["score"]
        sl_price = best["sl_price"]
        tp_price = best["tp_price"]

        ticker     = client.get_ticker(inst_id)
        live_price = float(ticker["last"]) if ticker else best["price"]

        # SL/TP من السعر الحي + ATR (لا السعر القديم) — RR=3:1 مع مسافة أوسع
        atr_val = best.get("atr", 0)
        if atr_val > 0:
            if signal == "buy":
                sl_price = live_price - 1.5 * atr_val
                tp_price = live_price + 4.5 * atr_val
            else:
                sl_price = live_price + 1.5 * atr_val
                tp_price = live_price - 4.5 * atr_val
        else:
            sl_price = live_price * (0.97 if signal == "buy" else 1.03)
            tp_price = live_price * (1.06 if signal == "buy" else 0.94)

        client.set_leverage(inst_id, LEVERAGE)
        # Use CAPITAL_RATIO=0.95 to leave a buffer for OKX fees & maintenance margin
        sz = client.calculate_contracts(inst_id, risk_capital, live_price, LEVERAGE, CAPITAL_RATIO)
        if sz <= 0:
            add_log(status, f"⏭️ {inst_id}: حجم صفر — التالي", "warning")
            continue

        result = client.place_order(inst_id, signal, sz, live_price,
                                    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
                                    sl_override=sl_price, tp_override=tp_price)
        if result["code"] == "0":
            direction = "شراء 📈" if signal == "buy" else "بيع 📉"
            add_log(status,
                f"✅ {direction} {inst_id} @ {live_price} | "
                f"درجة:{score} | رأس المال:${risk_capital:.2f}", "success")
            brain.record_open(memory, inst_id, signal, best["details"], live_price, score)
            status["total_trades"] = status.get("total_trades", 0) + 1
            trades_entered += 1
        else:
            # SL/TP order failed — try plain market order without attached algo
            detail = ""
            try:
                detail = result["data"][0].get("sMsg", "")
            except (KeyError, IndexError, TypeError):
                pass
            err_msg = detail or result.get("msg", "")
            add_log(status, f"⚠️ {inst_id}: {err_msg} — محاولة بدون SL/TP", "warning")

            result2 = client.place_order_no_sltp(inst_id, signal, sz)
            if result2["code"] == "0":
                direction = "شراء 📈" if signal == "buy" else "بيع 📉"
                add_log(status,
                    f"✅ {direction} {inst_id} @ {live_price} | "
                    f"درجة:{score} | (بدون SL/TP)", "success")
                brain.record_open(memory, inst_id, signal, best["details"], live_price, score)
                status["total_trades"] = status.get("total_trades", 0) + 1
                trades_entered += 1
            else:
                detail2 = ""
                try:
                    detail2 = result2["data"][0].get("sMsg", "")
                except (KeyError, IndexError, TypeError):
                    pass
                err_msg2 = detail2 or result2.get("msg", "خطأ غير معروف")
                add_log(status, f"⏭️ فشل {inst_id}: {err_msg2} — جرب التالي", "warning")


if __name__ == "__main__":
    asyncio.run(run())
