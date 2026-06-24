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


def _refresh_state_from_github():
    """Fetch latest state files from GitHub to avoid reading a stale local clone."""
    import urllib.request
    import base64 as b64
    token = os.environ.get('GH_TOKEN', '')
    repo  = os.environ.get('GITHUB_REPOSITORY', '')
    if not token or not repo:
        return
    for fname, path in [('bot_status.json', STATUS_FILE),
                         ('brain_memory.json', brain.MEMORY_FILE)]:
        try:
            url = f'https://api.github.com/repos/{repo}/contents/{fname}'
            req = urllib.request.Request(url, headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                content = b64.b64decode(data['content'])
                with open(path, 'wb') as f:
                    f.write(content)
            print(f'\U0001f504 {fname} محدَث من GitHub')
        except Exception:
            pass


async def run():
    # ── Validate credentials ──────────────────────────────────────────────────
    key    = os.environ.get("OKX_API_KEY", "").strip()
    secret = os.environ.get("OKX_API_SECRET", os.environ.get("OKX_SECRET_KEY","")).strip()
    phrase = os.environ.get("OKX_PASSPHRASE", "").strip()
    demo   = os.environ.get("OKX_IS_DEMO", "1").strip()

    if not key or not secret or not phrase:
        print("❌ Missing OKX credentials in GitHub Secrets.")
        sys.exit(1)

    os.environ["OKX_API_KEY"]    = key
    os.environ["OKX_API_SECRET"] = secret
    os.environ["OKX_SECRET_KEY"] = secret
    os.environ["OKX_PASSPHRASE"] = phrase
    os.environ["OKX_IS_DEMO"]    = demo

    _refresh_state_from_github()
    status = load_status()
    status["last_run"]  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status["mode"]      = "Demo \U0001f9ea" if demo != "0" else "Live \U0001f4b0"
    status["risk_mode"] = os.environ.get("RISK_MODE", "rocket").strip().lower()
    status.pop("stopped", None)   # امسح علامة الإيقاف القديمة عند كل تشغيل طبيعي

    # ── مفتاح إيقاف طارئ: إذا وُجد bot_stop.json أغلق كل الصفقات وانتهِ ──────
    STOP_FILE = os.path.join(os.path.dirname(__file__), "..", "bot_stop.json")
    if os.path.exists(STOP_FILE):
        add_log(status, "\U0001f6d1 bot_stop.json — إيقاف طارئ: إغلاق جميع الصفقات", "warning")
        from okx_client import OKXClient as _OKXClient
        _client = _OKXClient(key, secret, phrase, demo)
        _positions = _client.get_all_positions()
        _closed = []
        for _p in _positions:
            if float(_p.get("pos", 0)) != 0:
                if _client.close_position(_p["instId"]):
                    _closed.append(_p["instId"])
                    add_log(status, f"✅ أُغلق: {_p['instId']}", "success")
                else:
                    add_log(status, f"❌ فشل إغلاق: {_p['instId']}", "error")
        add_log(status,
            f"\U0001f6d1 البوت متوقف — {len(_closed)} صفقة مغلقة: {', '.join(_closed) or 'لا يوجد'}",
            "warning")
        status["stopped"] = True
        status["positions"] = []
        save_status(status)
        sys.exit(0)

    memory = brain.load_memory()

    add_log(status, "\U0001f680 تشغيل Snowball v22 + Brain...", "success")
    add_log(status, f"الوضع: {status['mode']}", "info")

    await _fallback_mscs(status, memory, key, secret, phrase, demo)

    # ── حفظ إحصائيات Brain في الحالة للعرض في لوحة التحكم ────────────────────
    status["brain_stats"] = brain.stats(memory)

    brain.save_memory(memory)
    save_status(status)
    print("✅ Done.")


def _trail_floor(peak):
    """
    وقف متحرك نسبي (uplRatio) — احتياطي ثانوي بعد الوقف الدولاري.
    يُسلَّح بعد +30% هامش (= +1.5% سعر) — حركة حقيقية تفوق ضجيج الدقيقة.
    يحمي التعادل عند 30-80%، يقفل 45% من القمة بعد 80%, ويقفل أكثر كلما ارتفع.
    """
    if peak < 0.30: return None          # تسليح بعد +30% هامش (+1.5% سعر عند x20)
    if peak < 0.80: return 0.0           # +30–80%: احمِ التعادل
    if peak < 1.80: return peak * 0.45   # +80–180%: اقفل 45% من القمّة
    if peak < 4.00: return peak * 0.60   # +180–400%: اقفل 60%
    if peak < 8.00: return peak * 0.70   # +400–800%: اقفل 70%
    return peak * 0.80                   # +800%+: اقفل 80% (رابح جامح)


def _trail_floor_pnl(peak_pnl):
    """
    أرضية الوقف المتحرّك بالدولار المطلق (PnL) — الطبقة الأساسية لقفل الربح.

    يحل مشكلة OKX Cross-Margin حيث uplRatio = upl/totalEquity (وليس upl/positionMargin)
    مما يجعل ربح المركز الفعلي يبدو صغيراً جداً كنسبة، فلا يُسلَّح الوقف النسبي.
    هنا نتتبّع ذروة الربح بالدولار ونقفل نسبة منها.

    مثال: مركز عند +$0.625 → peak_pnl=0.625 → floor = 0.625×0.55 = $0.344
    يُغلق إذا عاد UPL إلى $0.344 (يقفل $0.344 ربحاً).
    """
    if peak_pnl < 0.03: return None        # غير مُسلَّح: أقل من $0.03
    if peak_pnl < 0.10: return 0.00        # $0.03–$0.10: احمِ التعادل
    if peak_pnl < 0.30: return peak_pnl * 0.35   # $0.10–$0.30: اقفل 35%
    if peak_pnl < 1.00: return peak_pnl * 0.55   # $0.30–$1.00: اقفل 55%
    if peak_pnl < 5.00: return peak_pnl * 0.65   # $1–$5: اقفل 65%
    return peak_pnl * 0.75                  # $5+: اقفل 75% (الفارس الجامح)


def _equity_throttle(status, total_eq):
    """
    مُنظّم المخاطر حسب منحنى رأس المال (Equity-Curve Risk Throttle).

    كبرى صناديق التحوّط الكمّية لا تكتفي بضبط حجم كل صفقة، بل تتداول منحنى
    رأس مالها نفسه: تقلّص الحجم كلما تراجع رأس المال عن قمّته، وتعيده كاملاً
    عند التعافي. النجاة في فترات التراجع = استمرار التراكم نحو المليون.

    يتتبّع أعلى رأس مال (equity_peak) ويُرجع مُعامل ضرب لـ Kelly:
      تراجع <10%  → ×1.00 (حجم كامل)
      10–20%      → ×0.60
      20–35%      → ×0.35
      >35%        → 0.0 (أوقف الدخول الجديد حتى يتعافى رأس المال)

    دفاعي بحت: يقلّل المخاطرة فقط ولا يزيدها أبداً.
    عند تعذّر القياس (total_eq=0) يُرجع 1.0 فلا يعطّل التداول.
    """
    if total_eq <= 0:
        return 1.0
    peak = max(status.get("equity_peak", total_eq), total_eq)
    status["equity_peak"] = round(peak, 4)
    dd = (peak - total_eq) / peak if peak > 0 else 0.0
    status["drawdown"] = round(dd * 100, 2)
    if dd < 0.10: return 1.00
    if dd < 0.20: return 0.60
    if dd < 0.35: return 0.35
    return 0.0


def _manage_open_positions(status, client, positions):
    """
    مدير مخاطر برمجي كامل لكل مركز مفتوح (طبقات الحماية بالترتيب):
    1. قاطع دائرة: نسبة (-40%) أو خسارة مطلقة ($0.40) — أيّهما أولاً.
    2. HARD_TAKE: سقف أمان للمكاسب الجامحة (+200% هامش).
    3. وقف متحرك بالدولار (_trail_floor_pnl): الأساسي — يُسلَّح من $0.03.
    4. وقف متحرك نسبي (_trail_floor): احتياطي — يُسلَّح من +30% هامش.
    يُرجع مجموعة العملات التي أُغلقت هذه الدورة.
    """
    HARD_TAKE    = 2.00    # جني ربح عند +200% هامش
    HARD_STOP    = -0.40   # أغلق عند -40% هامش
    ABS_LOSS_USD = 0.40    # أغلق إذا تجاوزت الخسارة $0.40 مهما كانت النسبة

    peaks      = status.setdefault("peaks", {})
    pnl_peaks  = status.setdefault("pnl_peaks", {})
    closed_now = set()
    for p in positions:
        inst_id = p["instId"]
        try:
            ratio = float(p.get("uplRatio", 0))
            upl   = float(p.get("upl", 0))
            imr   = float(p.get("imr", 0))
            # احسب من upl/imr مباشرةً — OKX cross-margin قد يُعطي uplRatio مختلفاً
            if imr > 0:
                ratio = min(ratio, upl / imr)   # استخدم الأسوأ (الأكثر سلبيةً)
        except (ValueError, TypeError):
            upl   = 0.0
            ratio = 0.0

        peak = max(peaks.get(inst_id, ratio), ratio)
        peaks[inst_id] = peak
        peak_pnl = max(pnl_peaks.get(inst_id, upl), upl)
        pnl_peaks[inst_id] = peak_pnl

        # ── 1. قاطع الدائرة: نسبة أو قيمة مطلقة ───────────────────────────
        close_reason = None
        if ratio <= HARD_STOP:
            close_reason = f"{ratio*100:.0f}% (نسبة)"
        elif upl <= -ABS_LOSS_USD:
            close_reason = f"${abs(upl):.2f} (مطلق)"

        if close_reason:
            if client.close_position(inst_id):
                add_log(status,
                    f"\U0001f6d1 وقف طارئ {inst_id} عند {close_reason} — حماية رأس المال",
                    "warning")
                closed_now.add(inst_id)
                peaks.pop(inst_id, None)
                pnl_peaks.pop(inst_id, None)
            else:
                add_log(status,
                    f"⚠️ فشل إغلاق {inst_id} عند {close_reason} — سيُعاد في الجولة القادمة",
                    "error")
            continue

        # ── 2. سقف المكسب الجامح ───────────────────────────────────────────
        if ratio >= HARD_TAKE:
            if client.close_position(inst_id):
                add_log(status, f"\U0001f3af جني ربح {inst_id} عند +{ratio*100:.0f}%", "success")
                closed_now.add(inst_id)
                peaks.pop(inst_id, None)
                pnl_peaks.pop(inst_id, None)
            else:
                add_log(status, f"⚠️ فشل إغلاق {inst_id} عند جني الربح", "error")
            continue

        # ── 3. وقف متحرك بالدولار (الأساسي) ────────────────────────────────
        floor_pnl = _trail_floor_pnl(peak_pnl)
        if floor_pnl is not None and upl <= floor_pnl:
            if client.close_position(inst_id):
                add_log(status,
                    f"\U0001f512 وقف متحرك $ {inst_id}: قمّة +${peak_pnl:.3f} → ${upl:.3f} (قُفِل ${floor_pnl:.3f})",
                    "success")
                closed_now.add(inst_id)
                peaks.pop(inst_id, None)
                pnl_peaks.pop(inst_id, None)
            else:
                add_log(status, f"⚠️ فشل إغلاق {inst_id} عند الوقف الدولاري", "error")
            continue

        # ── 4. وقف متحرك نسبي (احتياطي) ────────────────────────────────────
        floor = _trail_floor(peak)
        if floor is not None and ratio <= floor:
            if client.close_position(inst_id):
                add_log(status,
                    f"\U0001f512 وقف متحرك % {inst_id}: قمّة +{peak*100:.0f}% → +{ratio*100:.0f}% (ربح مقفول)",
                    "success")
                closed_now.add(inst_id)
                peaks.pop(inst_id, None)
                pnl_peaks.pop(inst_id, None)
            else:
                add_log(status, f"⚠️ فشل إغلاق {inst_id} عند الوقف المتحرك", "error")

    active_ids = {p["instId"] for p in positions} - closed_now
    for k in list(peaks.keys()):
        if k not in active_ids:
            peaks.pop(k, None)
    for k in list(pnl_peaks.keys()):
        if k not in active_ids:
            pnl_peaks.pop(k, None)

    return closed_now


def _cancel_stale_maker_orders(status, client, memory, active):
    """
    يلغي أوامر maker الحدّية التي لم تُنفَّذ من الدورات السابقة، ويحذف سجلّاتها
    الوهمية (status=open) من ذاكرة الدماغ — حتى لا يتعلّم الدماغ من صفقة لم تحدث.
    يجب أن يُستدعى قبل خطوة كشف الصفقات المُغلقة (newly_closed) لتفادي تعلّم خاطئ.
    """
    pending = client.get_pending_orders()
    cancelled = []
    for od in pending:
        inst_id = od.get("instId", "")
        ord_id  = od.get("ordId", "")
        # لا تُلغِ أمراً لعملة لها مركز مفتوح فعلاً (قد يكون أمراً خوارزمياً)
        if inst_id in active or not ord_id:
            continue
        if client.cancel_order(inst_id, ord_id):
            cancelled.append(inst_id)

    # احذف الفتح الوهمي من الدماغ (الأمر لم يُنفَّذ → لا صفقة حقيقية)
    for sym in cancelled:
        for t in reversed(memory.get("trades", [])):
            if t["instId"] == sym and t["status"] == "open":
                memory["trades"].remove(t)
                break

    if cancelled:
        add_log(status,
            f"\U0001f9f9 أُلغيت {len(cancelled)} أوامر maker عالقة + نُظّفت من الدماغ", "info")


async def _fallback_mscs(status, memory, key, secret, phrase, demo):
    from okx_client import OKXClient
    from strategy import analyze
    import config as cfg

    LEVERAGE        = cfg.LEVERAGE
    STOP_LOSS_PCT   = cfg.STOP_LOSS_PCT
    TAKE_PROFIT_PCT = cfg.TAKE_PROFIT_PCT
    CAPITAL_RATIO   = cfg.CAPITAL_RATIO
    TOP_PAIRS       = cfg.SCAN_SYMBOLS

    add_log(status,
        f"⚙️ {cfg.RISK_MODE} | رافعة x{LEVERAGE} | مخاطرة {cfg.RISK_PER_TRADE*100:.0f}% | "
        f"مراكز {cfg.MAX_POSITIONS} | مسح {TOP_PAIRS} عملة | أوامر {cfg.ORDER_MODE}", "info")

    client = OKXClient(key, secret, phrase, demo)
    balance = client.get_balance()
    status["balance"] = round(balance, 4)
    add_log(status, f"\U0001f4b0 الرصيد: ${balance:.4f} USDT")

    # ── مُنظّم منحنى رأس المال: يقيس التراجع عن القمّة ويضبط حجم المخاطرة ────
    total_eq    = client.get_total_equity()
    eq_throttle = _equity_throttle(status, total_eq)
    if total_eq > 0:
        add_log(status,
            f"\U0001f4c9 رأس المال الكلي: ${total_eq:.2f} | القمّة ${status.get('equity_peak', total_eq):.2f} | "
            f"تراجع {status.get('drawdown', 0):.1f}% | مُنظّم ×{eq_throttle:.2f}", "info")

    prev_open = {p["instId"] for p in status.get("positions", [])}

    positions = client.get_all_positions()
    active    = {p["instId"] for p in positions if float(p.get("pos", 0)) != 0}
    status["positions"] = [
        {"instId": p["instId"],
         "side":   "شراء \U0001f4c8" if float(p.get("pos",0))>0 else "بيع \U0001f4c9",
         "entry":  float(p.get("avgPx",0)),
         "size":   abs(float(p.get("pos",0))),
         "pnl":    round(float(p.get("upl",0)),4)}
        for p in positions if float(p.get("pos",0)) != 0
    ]

    # ── نظّف أوامر maker العالقة أولاً (قبل كشف الصفقات المُغلقة) ────────────
    if cfg.ORDER_MODE == "maker":
        _cancel_stale_maker_orders(status, client, memory, active)

    # ── Detect closed positions → cooldown + brain learning ───────────────────
    believed_open = prev_open | brain.open_instruments(memory)
    newly_closed  = believed_open - active
    if newly_closed:
        for closed_id in newly_closed:
            brain.mark_exited(memory, closed_id)
            try:
                realized = client.get_last_realized_pnl(closed_id)
                ticker   = client.get_ticker(closed_id)
                exit_px  = float(ticker["last"]) if ticker else 0.0
                result   = brain.learn_from_closed(memory, closed_id, exit_px,
                                                    realized_pnl=realized)
                if result is not None:
                    src = "(فعلي)" if realized is not None else "(تقدير)"
                    outcome = "ربح ✅" if result == 1 else "خسارة ❌"
                    add_log(status, f"\U0001f9e0 Brain تعلّم: {closed_id} → {outcome} {src}", "info")
            except Exception:
                pass
        add_log(status,
            f"⏳ أُغلقت: {', '.join(newly_closed)} — "
            f"إعادة دخول بعد {brain.COOLDOWN_SECONDS} ثانية", "info")

    # ── وقف الخسارة المتحرك ──────────────────────────────────────────────────
    closed_by_trail = _manage_open_positions(status, client, positions)
    if closed_by_trail:
        active -= closed_by_trail

    # ── كم مركزاً يمكن فتحه الآن؟ ───────────────────────────────────────────
    MIN_BALANCE = 0.10
    # حد صلب: لا تتجاوز MAX_POSITIONS مهما كان توقيت استجابة OKX API
    if len(active) >= cfg.MAX_POSITIONS or balance < MIN_BALANCE:
        add_log(status, f"مراكز مفتوحة: {len(active)}/{cfg.MAX_POSITIONS} — لا دخول جديد")
        return

    # ملاحظة: حاجز إيقاف الدخول عند التراجع الحادّ أُزيل بطلب المستخدم —
    # الدخول برأس المال كاملاً مستمرّ دائماً مهما بلغ التراجع (استراتيجية تعافٍ).

    # مركز واحد فقط لكل دورة — يمنع فتح مراكز متعددة قبل تحديث OKX
    slots_available = 1

    pairs            = client.get_top_pairs(TOP_PAIRS)
    signals          = []
    skipped_losers   = 0
    skipped_cooldown = 0
    for inst_id in pairs:
        if inst_id in active:
            continue
        if not brain.can_reenter(memory, inst_id):
            skipped_cooldown += 1
            continue
        try:
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
        add_log(status, f"⏳ تخطّى {skipped_cooldown} عملة في فترة التهدئة", "info")
    if skipped_losers:
        add_log(status, f"\U0001f6ab تخطّى {skipped_losers} عملة خاسرة (Brain فلتر)", "info")

    signals.sort(key=lambda x: abs(x.get("adj_score", x["score"])), reverse=True)
    status["top_signals"] = [
        {"instId": s["instId"], "signal": s["signal"],
         "score": s["score"], "prob": round(s.get("prob",0.5),2)}
        for s in signals[:5]
    ]

    if not signals:
        add_log(status, "لا توجد إشارات كافية")
        return

    # ── حارس التركّز الاتجاهي: وازن المحفظة بين شراء وبيع لتقليل خطر الترابط ─
    long_ct  = sum(1 for p in positions if float(p.get("pos", 0)) > 0)
    short_ct = sum(1 for p in positions if float(p.get("pos", 0)) < 0)
    skew_cap = max(2, int(cfg.MAX_POSITIONS * 0.6))
    dominant = None
    if long_ct >= skew_cap and long_ct > short_ct:
        dominant = "buy"
    elif short_ct >= skew_cap and short_ct > long_ct:
        dominant = "sell"
    if dominant:
        opposite  = "sell" if dominant == "buy" else "buy"
        balancing = [s for s in signals if s["signal"] == opposite]
        if balancing:
            dom_ct = long_ct if dominant == "buy" else short_ct
            add_log(status,
                f"⚖️ تركّز {dominant} ({dom_ct}/{cfg.MAX_POSITIONS}) — "
                f"أُفضّل {opposite} لتوازن المحفظة وتقليل خطر الترابط", "info")
            signals = balancing

    # ── إحصائيات Brain (بدون Kelly — نستخدم رأس المال الكامل) ──────────────────
    wr = brain.current_win_rate(memory)
    add_log(status,
        f"\U0001f9e0 Brain WR={wr*100:.1f}% | مُنظّم ×{eq_throttle:.2f} | رأس المال الكامل ({CAPITAL_RATIO*100:.0f}%)", "info")

    trades_entered = 0
    for best in signals:
        if trades_entered >= slots_available:
            break

        inst_id  = best["instId"]
        signal   = best["signal"]
        score    = best["score"]

        ticker     = client.get_ticker(inst_id)
        live_price = float(ticker["last"]) if ticker else best["price"]

        # SL ثابت 0.5% | TP ثابت 1% من السعر الحي
        if signal == "buy":
            sl_price = live_price * (1 - STOP_LOSS_PCT)
            tp_price = live_price * (1 + TAKE_PROFIT_PCT)
        else:
            sl_price = live_price * (1 + STOP_LOSS_PCT)
            tp_price = live_price * (1 - TAKE_PROFIT_PCT)

        eff_leverage = LEVERAGE
        max_lev = client.get_max_leverage(inst_id)
        if max_lev and max_lev < LEVERAGE:
            eff_leverage = max_lev
            add_log(status, f"ℹ️ {inst_id}: رافعة {LEVERAGE}x→{eff_leverage:g}x (حد العملة)", "info")

        # حجم قابل للنجاة: نسبة محدودة من الرصيد (RISK_PER_TRADE) — الباكتيست أثبت
        # أن رأس المال الكامل يُصفّي الحساب عند أول سلسلة خسائر حتى لو كان الإعداد رابحاً.
        risk_capital = balance * cfg.RISK_PER_TRADE

        client.set_leverage(inst_id, eff_leverage)
        sz = client.calculate_contracts(inst_id, risk_capital, live_price, eff_leverage, CAPITAL_RATIO)
        if sz <= 0:
            add_log(status, f"⏭️ {inst_id}: حجم صفر (رصيد صغير جداً؟) — التالي", "warning")
            continue

        direction = "شراء \U0001f4c8" if signal == "buy" else "بيع \U0001f4c9"

        # ── وضع الأمر: maker (post-only، رسوم أقل) أو taker (سوق، فوري) ──────
        if cfg.ORDER_MODE == "maker":
            result = client.place_order_maker(inst_id, signal, sz, live_price,
                                              sl_price, tp_price, offset=cfg.MAKER_OFFSET)
            if result["code"] == "0":
                add_log(status,
                    f"\U0001f4e4 maker {direction} {inst_id} @~{live_price} | "
                    f"درجة:{score} | رأس المال:${risk_capital:.3f} | SL:{STOP_LOSS_PCT*100:.1f}% TP:{TAKE_PROFIT_PCT*100:.1f}% (بانتظار التنفيذ)", "success")
                brain.record_open(memory, inst_id, signal, best["details"], live_price, score)
                status["total_trades"] = status.get("total_trades", 0) + 1
                trades_entered += 1
            else:
                detail = ""
                try:
                    detail = result["data"][0].get("sMsg", "")
                except (KeyError, IndexError, TypeError):
                    pass
                err_msg = detail or result.get("msg", "خطأ غير معروف")
                add_log(status, f"⏭️ maker فشل {inst_id}: {err_msg} — التالي", "warning")
            continue

        # ── taker (أوامر سوق) ──────────────────────────────────────────────
        result = client.place_order(inst_id, signal, sz, live_price,
                                    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
                                    sl_override=sl_price, tp_override=tp_price)
        if result["code"] == "0":
            add_log(status,
                f"✅ {direction} {inst_id} @ {live_price} | "
                f"درجة:{score} | رأس المال:${risk_capital:.3f} | SL:{STOP_LOSS_PCT*100:.1f}% TP:{TAKE_PROFIT_PCT*100:.1f}%", "success")
            brain.record_open(memory, inst_id, signal, best["details"], live_price, score)
            status["total_trades"] = status.get("total_trades", 0) + 1
            trades_entered += 1
        else:
            detail = ""
            try:
                detail = result["data"][0].get("sMsg", "")
            except (KeyError, IndexError, TypeError):
                pass
            err_msg = detail or result.get("msg", "")
            add_log(status, f"⚠️ {inst_id}: {err_msg} — محاولة بدون SL/TP", "warning")

            result2 = client.place_order_no_sltp(inst_id, signal, sz)
            if result2["code"] == "0":
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
