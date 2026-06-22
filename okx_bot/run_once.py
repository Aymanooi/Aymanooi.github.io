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
    status["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["mode"]     = "Demo 🧪" if demo != "0" else "Live 💰"

    memory = brain.load_memory()

    # ── Import and run Snowball bot (one cycle) ───────────────────────────────
    add_log(status, "🚀 تشغيل Snowball v22 + Brain...", "success")
    add_log(status, f"الوضع: {status['mode']}", "info")

    try:
        from snowball import UltimateFinalBot, config, log as slog

        bot = UltimateFinalBot()

        # ── Initialize exchange + data ────────────────────────────────────────
        add_log(status, "⚙️ الاتصال بـ OKX...", "info")
        await bot.exchange.connect()

        # Fetch top symbols data
        symbols = config.SYMBOLS_TIER1[:50]
        add_log(status, f"📊 تحليل {len(symbols)} عملة...", "info")

        # Fetch OHLCV for all symbols
        await bot._fetch_all_data()

        # ── Balance ───────────────────────────────────────────────────────────
        if config.PAPER_TRADING:
            equity = bot.paper.balance
        else:
            try:
                balance_data = await bot.exchange.fetch_balance()
                equity = float(balance_data.get("USDT", {}).get("free", 0))
            except Exception:
                equity = bot.paper.balance
        status["balance"] = round(equity, 4)
        add_log(status, f"💰 الرصيد: ${equity:.4f} USDT", "info")

        # ── MillionDollarProtocol update ──────────────────────────────────────
        mdp_result = bot.mdp.update(equity)
        add_log(status,
            f"🎯 الوضع: {mdp_result['mode']} | "
            f"رافعة: x{mdp_result['settings']['leverage']} | "
            f"نمو: ×{mdp_result['growth_x']}",
            "info")
        if mdp_result.get("milestone"):
            add_log(status,
                f"🏆 معلم جديد: ${mdp_result['milestone']:,.0f}!",
                "success")

        # ── Manage open positions ─────────────────────────────────────────────
        await bot._manage_positions()

        # ── Snowball + Compound Engine ────────────────────────────────────────
        bot.snowball.record(equity)
        bot.compound_eng.record(equity)
        compound_summary = bot.compound_eng.compound_summary(equity)
        add_log(status, compound_summary.split("\n")[0], "info")

        # ── Scan for signals ──────────────────────────────────────────────────
        n_before = len(bot.positions)
        await bot._scan_signals(size_mult=1.0)
        n_after  = len(bot.positions)

        if n_after > n_before:
            add_log(status, f"✅ دخلنا {n_after - n_before} صفقة جديدة!", "success")
            status["total_trades"] = status.get("total_trades", 0) + (n_after - n_before)
        else:
            add_log(status, "لا توجد إشارات كافية في هذه الدورة", "info")

        # ── Open positions summary ────────────────────────────────────────────
        positions_out = []
        for sym, pos in bot.positions.items():
            positions_out.append({
                "instId": sym,
                "side":   "شراء 📈" if pos.get("direction") == "LONG" else "بيع 📉",
                "entry":  round(float(pos.get("entry", 0)), 6),
                "size":   round(float(pos.get("qty", 0)), 4),
                "pnl":    round(float(pos.get("pnl", 0)), 4),
            })
        status["positions"]      = positions_out
        status["open_positions"] = len(positions_out)

        # ── Performance stats ─────────────────────────────────────────────────
        perf = bot.paper.performance()
        status["win_rate"]  = perf.get("win_rate", 0)
        status["sharpe"]    = round(perf.get("sharpe", 0), 2)
        status["mdp_mode"]  = mdp_result["mode"]
        status["growth_x"]  = mdp_result["growth_x"]

        # ── Brain: learn from any newly closed positions ───────────────────────
        for trade in bot.paper.closed_trades[-5:]:
            sym = trade.get("symbol", "")
            if sym:
                details = {"EMA": 10, "RSI": 5, "MACD": 5, "BB": 5,
                           "Stoch": 3, "Volume": 3, "Pattern": 2, "HTF_1h": 5}
                won = 1 if trade.get("pnl", 0) > 0 else 0
                if won:
                    memory["wins"]   = memory.get("wins", 0) + 1
                else:
                    memory["losses"] = memory.get("losses", 0) + 1

        status["brain"] = brain.stats(memory)
        wr = brain.current_win_rate(memory)
        add_log(status,
            f"🧠 Brain — معدل الفوز: {wr*100:.1f}% | "
            f"Kelly: {brain.kelly_fraction(wr)*100:.1f}%",
            "info")

        # ── Volatility scanner top 5 ──────────────────────────────────────────
        top5 = bot.vol_scanner.scan(bot.data_cache)
        if top5:
            add_log(status, f"⚡ أعلى تقلباً: {' | '.join(top5[:5])}", "info")
        status["top_volatile"] = top5[:5]

    except ImportError as e:
        add_log(status, f"⚠️ Snowball import error: {e} — falling back to MSCS", "warning")
        await _fallback_mscs(status, memory, key, secret, phrase, demo)
    except Exception as e:
        add_log(status, f"❌ خطأ: {str(e)[:200]}", "error")
        import traceback
        print(traceback.format_exc())

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

    if active or balance < 1:
        add_log(status, f"صفقة مفتوحة أو رصيد منخفض — لا دخول جديد")
        return

    pairs   = client.get_top_pairs(TOP_PAIRS)
    signals = []
    for inst_id in pairs:
        try:
            c15 = client.get_candles(inst_id, bar="15m", limit=60)
            c1h = client.get_candles(inst_id, bar="1H", limit=60)
            r   = analyze(c15, c1h)
            if r["signal"]:
                adj, prob = brain.adjusted_score(r["details"], memory)
                signals.append({"instId": inst_id, **r,
                                 "adj_score": adj, "prob": prob})
        except Exception:
            continue

    signals.sort(key=lambda x: abs(x.get("adj_score", x["score"])), reverse=True)
    status["top_signals"] = [
        {"instId": s["instId"], "signal": s["signal"],
         "score": s["score"], "prob": round(s.get("prob",0.5),2)}
        for s in signals[:5]
    ]

    if not signals:
        add_log(status, "لا توجد إشارات كافية")
        return

    best     = signals[0]
    inst_id  = best["instId"]
    signal   = best["signal"]
    score    = best["score"]
    sl_price = best["sl_price"]
    tp_price = best["tp_price"]

    ticker     = client.get_ticker(inst_id)
    live_price = float(ticker["last"]) if ticker else best["price"]
    sl_price   = sl_price or (live_price * (0.98 if signal=="buy" else 1.02))
    tp_price   = tp_price or (live_price * (1.04 if signal=="buy" else 0.96))

    client.set_leverage(inst_id, LEVERAGE)
    wr    = brain.current_win_rate(memory)
    kelly = brain.kelly_fraction(wr, rr=3.0, cap=cfg.KELLY_CAP)
    # Risk = min(Kelly, configured per-trade cap) of balance — never the full balance
    risk_frac    = min(kelly, cfg.RISK_PER_TRADE) if cfg.RISK_MODE != "aggressive" else kelly
    risk_capital = balance * risk_frac
    sz    = client.calculate_contracts(inst_id, risk_capital, live_price, LEVERAGE, 1.0)
    if sz <= 0:
        add_log(status, f"{inst_id}: حجم صفر", "warning")
        return

    result = client.place_order(inst_id, signal, sz, live_price,
                                STOP_LOSS_PCT, TAKE_PROFIT_PCT,
                                sl_override=sl_price, tp_override=tp_price)
    if result["code"] == "0":
        direction = "شراء 📈" if signal == "buy" else "بيع 📉"
        add_log(status,
            f"✅ {direction} {inst_id} @ {live_price} | "
            f"درجة:{score} | Kelly:{kelly*100:.0f}% | مخاطرة:${risk_capital:.3f}", "success")
        brain.record_open(memory, inst_id, signal, best["details"], live_price, score)
        status["total_trades"] = status.get("total_trades", 0) + 1
    else:
        add_log(status, f"❌ فشل: {result.get('msg','')}", "error")


if __name__ == "__main__":
    asyncio.run(run())
