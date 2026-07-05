"""
run_once.py — GitHub Actions entry point
Runs ONE cycle of the Snowball v22 bot, saves status + brain memory.
"""
import asyncio
import os
import sys
import json
import time
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
        # إلغاء أوامر maker المعلّقة أولاً — حتى لا يُنفَّذ أمر بعد الإيقاف
        # فيفتح صفقة بلا إدارة
        for _o in _client.get_pending_orders():
            if _client.cancel_order(_o["instId"], _o["ordId"]):
                add_log(status, f"🧹 أُلغي أمر معلّق: {_o['instId']}", "info")
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

    # ── حلقة داخلية: عدة فحوصات بفاصل 30 ثانية في التشغيلة الواحدة ──────────
    # ضريبة تجهيز GitHub Actions (checkout + pip ≈ دقيقة) تُدفع مرة واحدة،
    # ثم يتكرر الفحص كل BOT_RESCAN_SECONDS حتى نفاد BOT_LOOP_MINUTES —
    # فيصير الدخول في عملة جديدة بعد الخروج خلال ~30 ثانية بدل 2-4 دقائق.
    # الميزانية 6 دقائق: آخر فحص قد يمتد ~75 ثانية + حفظ الحالة + جدولة
    # الدورة التالية، فنبقى تحت سقف timeout-minutes: 10 بهامش مريح.
    loop_minutes   = float(os.environ.get("BOT_LOOP_MINUTES", "6"))
    rescan_seconds = float(os.environ.get("BOT_RESCAN_SECONDS", "30"))
    deadline = time.monotonic() + loop_minutes * 60

    while True:
        await _fallback_mscs(status, memory, key, secret, phrase, demo)

        # حفظ إحصائيات Brain والحالة بعد كل فحص (لا عند النهاية فقط) حتى
        # لا يضيع تعلّم الدماغ لو قُتلت التشغيلة بالـtimeout
        status["brain_stats"] = brain.stats(memory)
        brain.save_memory(memory)
        save_status(status)

        if time.monotonic() + rescan_seconds >= deadline:
            break
        await asyncio.sleep(rescan_seconds)
        status["last_run"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC")

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


def _explosion_score(candles):
    """
    درجة «ما قبل الانفجار» (طلب المستخدم: الدخول قبل انفجار العملة
    صعوداً أو هبوطاً) — تجمع الظاهرتين الموثقتين اللتين تسبقان
    الحركات الكبيرة:

      • انضغاط التقلب (squeeze): نطاق آخر 12 دقيقة أضيق بكثير من نطاق
        الـ48 دقيقة السابقة = نابض مضغوط لم ينطلق بعد.
      • تدفق الحجم: حجم آخر 5 دقائق أعلى بوضوح من متوسط ما قبله =
        وقود يتدفق قبل الحركة.

    الدرجة = انضغاط × تدفق (كلاهما مسقوف بـ5 ضد شذوذ البيانات).
    عملة منفجرة أصلاً تحصل على انضغاط منخفض فتتأخر في الترتيب —
    نريد التي على وشك الانفجار، لا التي انفجرت.
    """
    try:
        ch = sorted(candles, key=lambda x: int(x[0]))
        if len(ch) < 60:
            return 0.0
        highs  = [float(x[2]) for x in ch]
        lows   = [float(x[3]) for x in ch]
        closes = [float(x[4]) for x in ch]
        vols   = [float(x[5]) for x in ch]
        px = closes[-1]
        if px <= 0:
            return 0.0
        recent_range = (max(highs[-12:]) - min(lows[-12:])) / px
        prior_range  = (max(highs[-60:-12]) - min(lows[-60:-12])) / px
        compression  = min(prior_range / (recent_range + 1e-9), 5.0)
        vol_recent = sum(vols[-5:]) / 5.0
        vol_base   = sum(vols[-35:-5]) / 30.0
        vol_surge  = min(vol_recent / (vol_base + 1e-9), 5.0)
        return round(compression * vol_surge, 3)
    except Exception:
        return 0.0


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
    إدارة المراكز — وضع "اترك الصفقة تركض حتى SL/TP الحقيقي" (طلب المستخدم).

    أوامر SL (0.5%) و TP (1%) مربوطة على منصّة OKX نفسها وقت الفتح، فهي التي
    تُغلق الصفقة بدقّة عند ضرب السعر. لذا عُطِّلت كل عمليات الإغلاق المبكر من
    جانب بايثون (قاطع $0.40 + الوقفان المتحركان) لأنها كانت تغلق قبل بلوغ
    0.5%/1% (مثلاً $0.40 = حركة 0.16% فقط على x20).

    تبقى فقط شبكة أمان كارثية لا تتدخّل أبداً قبل الوقف الحقيقي، وتعمل فقط لو
    فشل ربط أمر SL على المنصّة:
      • HARD_STOP = -40% هامش (= -2% سعر) ≫ وقفك 0.5% (-10% هامش)
      • HARD_TAKE = +200% هامش (= +10% سعر) ≫ هدفك 1% (+20% هامش)
    """
    HARD_TAKE = 2.00    # شبكة أمان للمكاسب الجامحة (لا تتدخّل قبل TP 1%)
    HARD_STOP = -0.40   # شبكة أمان كارثية (لا تتدخّل قبل SL 0.5%)

    closed_now = set()
    for p in positions:
        inst_id = p["instId"]
        try:
            ratio = float(p.get("uplRatio", 0))
            upl   = float(p.get("upl", 0))
            imr   = float(p.get("imr", 0))
            if imr > 0:
                ratio = min(ratio, upl / imr)
        except (ValueError, TypeError):
            ratio = 0.0

        # شبكة أمان كارثية فقط — تعمل لو فشل أمر SL/TP على المنصّة
        if ratio <= HARD_STOP or ratio >= HARD_TAKE:
            label = f"{ratio*100:.0f}%"
            if client.close_position(inst_id):
                add_log(status,
                    f"\U0001f6d1 شبكة أمان {inst_id} عند {label} هامش — أمر المنصّة فشل غالباً",
                    "warning")
                closed_now.add(inst_id)
            else:
                add_log(status, f"⚠️ فشل إغلاق {inst_id} عند شبكة الأمان", "error")

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
    from strategy import analyze, stochastic, rsi
    import config as cfg

    LEVERAGE        = cfg.LEVERAGE
    STOP_LOSS_PCT   = cfg.STOP_LOSS_PCT
    TAKE_PROFIT_PCT = cfg.TAKE_PROFIT_PCT
    CAPITAL_RATIO   = cfg.CAPITAL_RATIO
    TOP_PAIRS       = cfg.SCAN_SYMBOLS

    _lev_label = "أقصى/عملة" if getattr(cfg, "USE_MAX_LEVERAGE", False) else f"x{LEVERAGE}"
    add_log(status,
        f"⚙️ {cfg.RISK_MODE} | رافعة {_lev_label} | مخاطرة {cfg.RISK_PER_TRADE*100:.0f}% | "
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

    # ── أكّد تنفيذ أوامر maker: أي مركز ظهر نشطاً فعلاً → علّمه filled ────────
    # هذا يميّز الصفقة الحقيقية عن أمر maker لم يُنفَّذ (الذي يُسمّم الدماغ كخسارة وهمية)
    for p in positions:
        if float(p.get("pos", 0)) != 0:
            brain.mark_filled(memory, p["instId"], float(p.get("avgPx", 0)) or None)

    # ── نظّف أوامر maker العالقة أولاً (قبل كشف الصفقات المُغلقة) ────────────
    if cfg.ORDER_MODE == "maker":
        _cancel_stale_maker_orders(status, client, memory, active)

    # ── Detect closed positions → cooldown + brain learning ───────────────────
    believed_open = prev_open | brain.open_instruments(memory)
    newly_closed  = believed_open - active
    if newly_closed:
        phantom_discarded = []
        learned_ids       = []
        for closed_id in newly_closed:
            # حارس الصفقات الوهمية: أمر maker سُجّل لكنه لم يُنفَّذ قطّ (filled=False).
            # لا نتعلّم منه كخسارة — نحذفه بهدوء حتى لا يُسمّم الدماغ ومعدّل الفوز.
            if brain.open_instruments(memory) and not brain.is_filled(memory, closed_id) \
               and closed_id not in prev_open:
                if brain.discard_open(memory, closed_id):
                    phantom_discarded.append(closed_id)
                    continue
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
                    learned_ids.append(closed_id)
                    add_log(status, f"\U0001f9e0 Brain تعلّم: {closed_id} → {outcome} {src}", "info")
            except Exception:
                pass
        if phantom_discarded:
            add_log(status,
                f"\U0001f47b حُذف {len(phantom_discarded)} أمر maker لم يُنفَّذ "
                f"(ليست خسائر — لا تُسمّم الدماغ)", "info")
        if learned_ids:
            add_log(status,
                f"⏳ أُغلقت: {', '.join(learned_ids)} — "
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

    # ── بوّابة النظام التكيّفية (Regime Gate) — أثبت الباكتيست أنها ترفع PF ──
    # توقف الدخول حين يكون النظام خاسراً مؤقتاً (آخر صفقات معدّل فوزها منخفض)،
    # وتستأنف تلقائياً حين يتحسّن. تتجنّب النوافذ الخاسرة.
    # وضع التناوب الدائم (طلب المستخدم): عند الخروج من عملة ندخل أخرى في
    # الفحص التالي (~30 ثانية) — لا ننتظر مرشحاً مثالياً ولا بوّابة النظام.
    always_in = os.environ.get("BOT_ALWAYS_IN", "1").strip() != "0"

    if getattr(cfg, "REGIME_GATE", False):
        if not brain.regime_ok(memory,
                               window=getattr(cfg, "REGIME_WINDOW", 8),
                               min_wr=getattr(cfg, "REGIME_MIN_WR", 0.40),
                               max_age_seconds=getattr(cfg, "REGIME_MAX_AGE", 3600)):
            # مع التناوب الدائم: البوّابة لا تمنع ملء الخانات الفارغة —
            # وصلنا هنا فقط إذا كانت هناك خانة فارغة (الفحص أعلاه)
            if not always_in:
                add_log(status,
                    "\U0001f6e1️ بوّابة النظام: آخر الصفقات خاسرة — إيقاف الدخول مؤقتاً حتى يتحسّن النظام",
                    "warning")
                return
            add_log(status,
                "\U0001f6e1️ بوّابة النظام خاسرة مؤقتاً — التناوب الدائم مفعّل: نواصل الدخول",
                "warning")

    # مركز واحد فقط لكل دورة — يمنع فتح مراكز متعددة قبل تحديث OKX
    slots_available = 1

    pairs            = client.get_top_pairs(TOP_PAIRS, min_usd_vol=cfg.MIN_USD_VOL_24H)
    signals          = []
    relaxed          = []   # إشارة تجاوزت العتبة لكن رفضتها فلاتر تأكيد الأطر
    weak             = []   # درجة تحت العتبة (احتياط أخير للتناوب الدائم)
    skipped_losers   = 0
    skipped_cooldown = 0
    skipped_mom      = 0
    skipped_slow     = 0
    # 📊 فلتر الحركة اليومية (طلب المستخدم: صعود > MOM_UP% أو هبوط >
    # MOM_DOWN% خلال 24 ساعة فقط). خريطة التغيّر بنداء واحد.
    change_map = client.get_change_map() if getattr(cfg, "MOMENTUM_FILTER", False) else {}
    for inst_id in pairs:
        if inst_id in active:
            continue
        # ⛔ حظر الأصول (طلب المستخدم): لا دخول في BTC/ETH/SOL/XAU
        if any(b in inst_id.upper() for b in getattr(cfg, "BANNED_ASSETS", ())):
            continue
        # 📊 فلتر الحركة: لا دخول إلا صعود > +MOM_UP% أو هبوط < −MOM_DOWN%
        if getattr(cfg, "MOMENTUM_FILTER", False):
            chg = change_map.get(inst_id)
            if chg is None:
                continue
            up = getattr(cfg, "MOM_UP_PCT", 10.0)
            dn = getattr(cfg, "MOM_DOWN_PCT", 5.0)
            if not (chg >= up or chg <= -dn):
                skipped_mom += 1
                continue
        # 🐸 حصري على الميم (طلب المستخدم: الدخول فقط في عملات الميم):
        # تخطَّ أي عملة ليست في قائمة الميم تماماً كالمحظورة.
        if getattr(cfg, "MEME_ONLY", False):
            _base = inst_id.split("-")[0].upper()
            if _base not in tuple(m.upper() for m in getattr(cfg, "MEME_ASSETS", ())):
                continue
        if not brain.can_reenter(memory, inst_id):
            skipped_cooldown += 1
            continue
        try:
            if cfg.FILTER_LOSERS and not brain.should_trade_symbol(memory, inst_id):
                skipped_losers += 1
                continue
            # 1m للإشارة + 5m للإطار الأعلى — مطابق للباكتيست الذي أثبت PF=1.07
            # عند x3 (الرافعة المُثلى) ينمو الحساب؛ x20 يُصفّيه رغم نفس الحافة.
            c15 = client.get_candles(inst_id, bar="1m", limit=100)
            c1h = client.get_candles(inst_id, bar="5m",  limit=60)
            r   = analyze(c15, c1h)
            # 💲 فلتر نطاق السعر (طلب المستخدم: الدخول فقط في العملات بين
            # ~صفر و 1 دولار). العملات الرخيصة/الميكرو — تنسجم مع الميم
            # والسرعة الهائلة. نتخطّى أي عملة خارج النطاق.
            _px = float(r.get("price") or 0)
            _pmin = getattr(cfg, "MIN_PRICE_USD", 0.0)
            _pmax = getattr(cfg, "MAX_PRICE_USD", 0.0)
            if _pmax and _px > _pmax:
                continue
            if _px <= _pmin:
                continue
            # ⚡ فلتر السرعة الصارم (طلب المستخدم: الدخول فقط في العملات
            # التي تتحرك بسرعة هائلة). ATR% لكل دقيقة = مقياس السرعة؛
            # نتخطّى أي عملة سرعتها دون MIN_ATR_PCT.
            _atr_pct = (float(r.get("atr") or 0) / _px * 100.0) if _px > 0 else 0.0
            r["atr_pct"] = round(_atr_pct, 3)
            _min_spd = getattr(cfg, "MIN_ATR_PCT", 0.0)
            if _min_spd and _atr_pct < _min_spd:
                skipped_slow += 1
                continue
            # درجة «ما قبل الانفجار» لكل مرشح — تُستخدم في ترتيب الاختيار
            r["explosion"] = _explosion_score(c15)
            if r["signal"]:
                # ── تأكيد الإطار الأعلى (HTF 5m) — أقوى استراتيجية مُختبَرة ──
                # لا تدخل إلا إذا اتّفق اتجاه الـ5m مع إشارة الـ1m.
                # الباكتيست: PF 1.09→1.29، $3.67→$5.12 (+39%). نتداول مع الترند الأكبر.
                if getattr(cfg, "HTF_CONFIRM", False) and len(c1h) >= 2:
                    sig_dir = 1 if r["signal"] == "buy" else -1
                    htf = sorted(c1h, key=lambda x: int(x[0]))
                    htf_dir = 1 if float(htf[-1][4]) > float(htf[-2][4]) else -1
                    if htf_dir != sig_dir:
                        relaxed.append({"instId": inst_id, **r})
                        continue   # الإطار 5m يعارض — تخطّ
                    # تأكيد ثلاثي: 15m أيضاً يجب أن يتّفق (أقوى استراتيجية: PF 1.28→1.49)
                    if getattr(cfg, "HTF_15M_CONFIRM", False):
                        c15m = client.get_candles(inst_id, bar="15m", limit=30)
                        if len(c15m) >= 2:
                            h15 = sorted(c15m, key=lambda x: int(x[0]))
                            d15 = 1 if float(h15[-1][4]) > float(h15[-2][4]) else -1
                            if d15 != sig_dir:
                                relaxed.append({"instId": inst_id, **r})
                                continue   # الإطار 15m يعارض — تخطّ
                    # تأكيد الإطار الرابع 1H (أقوى نظام: PF 1.38→1.69 خارج العيّنة)
                    if getattr(cfg, "HTF_1H_CONFIRM", False):
                        c1hr = client.get_candles(inst_id, bar="1H", limit=30)
                        if len(c1hr) >= 2:
                            hh = sorted(c1hr, key=lambda x: int(x[0]))
                            d1h = 1 if float(hh[-1][4]) > float(hh[-2][4]) else -1
                            if d1h != sig_dir:
                                relaxed.append({"instId": inst_id, **r})
                                continue   # الإطار 1H يعارض — تخطّ
                # ── تأكيد Stochastic — لا تدخل والمؤشّر مُنهَك (PF 1.49→2.09 بالباكتيست) ──
                if getattr(cfg, "STOCH_CONFIRM", False):
                    ch = sorted(c15, key=lambda x: int(x[0]))
                    kk, _ = stochastic([float(x[2]) for x in ch],
                                       [float(x[3]) for x in ch],
                                       [float(x[4]) for x in ch])
                    if (r["signal"] == "buy" and kk >= 80) or \
                       (r["signal"] == "sell" and kk <= 20):
                        relaxed.append({"instId": inst_id, **r})
                        continue   # المؤشّر مُنهَك — تخطّ
                # ── RSI معتدل — أقوى استراتيجية صمدت خارج العيّنة (PF 1.17→1.30، ضِعف) ──
                # لا تدخل عند RSI متطرّف؛ نتجنّب الدخول المُنهَك. شراء 40-68، بيع 32-60.
                if getattr(cfg, "RSI_MODERATE", False):
                    chr_=sorted(c15, key=lambda x: int(x[0]))
                    rv=rsi([float(x[4]) for x in chr_], 14)
                    if (r["signal"]=="buy"  and not (40 <= rv <= 68)) or \
                       (r["signal"]=="sell" and not (32 <= rv <= 60)):
                        relaxed.append({"instId": inst_id, **r})
                        continue
                adj, prob = brain.adjusted_score(r["details"], memory)
                signals.append({"instId": inst_id, **r,
                                 "adj_score": adj, "prob": prob})
            elif abs(r.get("score", 0)) >= 15:
                # لا إشارة (تحت العتبة) لكن الدرجة ليست ضجيجاً صرفاً —
                # احتياط أخير لوضع التناوب الدائم
                weak.append({"instId": inst_id, **r})
        except Exception:
            continue

    if skipped_cooldown:
        add_log(status, f"⏳ تخطّى {skipped_cooldown} عملة في فترة التهدئة", "info")
    if skipped_losers:
        add_log(status, f"\U0001f6ab تخطّى {skipped_losers} عملة خاسرة (Brain فلتر)", "info")
    if skipped_mom:
        add_log(status,
            f"📊 تخطّى {skipped_mom} عملة خارج نطاق الحركة "
            f"(صعود>+{getattr(cfg,'MOM_UP_PCT',10):.0f}% أو هبوط<−{getattr(cfg,'MOM_DOWN_PCT',5):.0f}%)",
            "info")
    if skipped_slow:
        add_log(status,
            f"⚡ تخطّى {skipped_slow} عملة بطيئة (سرعة < {getattr(cfg,'MIN_ATR_PCT',0):.2f}% ATR/دقيقة)",
            "info")

    # 🐸 تفضيل عملات الميم (طلب المستخدم): إن وُجد مرشح ميم مؤهَّل في أي
    # قائمة نُبقي الميم فقط فيها؛ وإلا نُبقيها كما هي (رجوع لبقية العملات
    # حتى لا يبقى البوت خارج السوق). يُطبَّق على القوائم الثلاث بثبات.
    if getattr(cfg, "MEME_PREFER", False):
        memes = tuple(m.upper() for m in getattr(cfg, "MEME_ASSETS", ()))

        def _is_meme(inst_id):
            base = inst_id.split("-")[0].upper()
            return base in memes

        def _meme_first(pool):
            m = [s for s in pool if _is_meme(s["instId"])]
            return m if m else pool

        n_before = len(signals)
        signals = _meme_first(signals)
        relaxed = _meme_first(relaxed)
        weak    = _meme_first(weak)
        if signals and n_before and len(signals) < n_before:
            add_log(status,
                f"🐸 تفضيل الميم: {len(signals)} مرشح ميم من {n_before}", "info")

    # ترتيب «السرعة أولاً» (طلب المستخدم الصريح: الدخول في العملات التي
    # تتحرك بسرعة كبيرة جداً). درجة مركّبة متصلة تدمج العاملين فعلاً بدل
    # المقارنة التسلسلية التي كانت تجعل الانفجار يحسم كل شيء والسرعة
    # لا تؤثر:
    #   الدرجة = ATR% × (1 + درجة الانفجار)
    # → الأسرع حركة يتصدّر، معزّزاً بمن هو على وشك الانفجار (النابض
    #   المضغوط ذو الحجم المتدفق). قوة الإشارة كاسر تعادل أخير.
    def _speed_key(s):
        price = float(s.get("price") or 0)
        atr   = float(s.get("atr") or 0)
        atr_pct = (atr / price) if price > 0 else 0.0
        composite = atr_pct * (1.0 + float(s.get("explosion", 0.0)))
        s["speed_score"] = round(composite, 5)
        return (composite, abs(s.get("adj_score", s.get("score", 0))))

    signals.sort(key=_speed_key, reverse=True)
    status["top_signals"] = [
        {"instId": s["instId"], "signal": s["signal"],
         "score": s["score"], "prob": round(s.get("prob",0.5),2)}
        for s in signals[:5]
    ]

    if not signals and always_in:
        # ── التناوب الدائم (طلب المستخدم): خانة فارغة ولا مرشح مؤكَّد —
        # ندخل أفضل مرشح متاح بدل الانتظار: أولاً من رفضتهم فلاتر الأطر
        # (إشارة حقيقية فوق العتبة)، وإلا فأقوى درجة خام ≥ 15.
        # (لا نصل هنا إلا وهناك خانة فارغة — الفحص المبكر أعلاه يعيد قبلها)
        pool, label = (relaxed, "رفضته فلاتر الأطر") if relaxed else \
                      (weak,    "درجة تحت العتبة")
        if pool:
            pool.sort(key=_speed_key, reverse=True)
            pick = pool[0]
            if not pick.get("signal"):
                pick["signal"] = "buy" if pick.get("score", 0) > 0 else "sell"
            adj, prob = brain.adjusted_score(pick.get("details", {}), memory)
            pick["adj_score"], pick["prob"] = adj, prob
            signals = [pick]
            add_log(status,
                f"🔄 تناوب دائم: دخول أفضل مرشح ({label}) "
                f"{pick['instId']} درجة {pick.get('score', 0)}", "info")

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
        f"\U0001f9e0 Brain WR={wr*100:.1f}% | مُنظّم ×{eq_throttle:.2f} | رأس المال الكامل ({CAPITAL_RATIO*100:.0f}%) موزّع على {cfg.MAX_POSITIONS} مراكز", "info")

    trades_entered = 0
    for best in signals:
        if trades_entered >= slots_available:
            break

        inst_id  = best["instId"]
        signal   = best["signal"]
        score    = best["score"]

        # 🔄 عكس الإشارة (طلب المستخدم): لو أعطى البوت شراء ندخل بيعاً
        # والعكس — اختبار فرضية «اعكس الخاسر لتربح». التنفيذ فقط يُعكس؛
        # المنطق والتأكيدات تبقى كما هي. SL/TP تُحسب من signal فتتبعه.
        if getattr(cfg, "REVERSE_SIGNAL", False) and signal in ("buy", "sell"):
            signal = "sell" if signal == "buy" else "buy"

        ticker     = client.get_ticker(inst_id)
        live_price = float(ticker["last"]) if ticker else best["price"]

        # ── SL/TP متغيّران حسب تقلّب العملة (ATR) — طلب المستخدم ──────────────
        # كل عملة تأخذ وقفاً وهدفاً يناسبان تذبذبها: SL=1.5×ATR، TP=4.5×ATR.
        # نسبة الربح/الخسارة 3:1 → التعادل عند فوز 25% فقط (الثابت 0.5/1% طلب 66%+).
        atr_val = float(best.get("atr", 0.0) or 0.0)
        if cfg.VARIABLE_RISK and atr_val > 0 and live_price > 0:
            sl_dist = cfg.ATR_SL_MULT * atr_val
            tp_dist = cfg.ATR_TP_MULT * atr_val
        else:
            # احتياط: لو تعذّر ATR ارجع للنسب الثابتة
            sl_dist = live_price * STOP_LOSS_PCT
            tp_dist = live_price * TAKE_PROFIT_PCT
        sl_move = (sl_dist / live_price) if live_price > 0 else STOP_LOSS_PCT
        tp_move = (tp_dist / live_price) if live_price > 0 else TAKE_PROFIT_PCT
        if signal == "buy":
            sl_price = round(live_price - sl_dist, 8)
            tp_price = round(live_price + tp_dist, 8)
        else:
            sl_price = round(live_price + sl_dist, 8)
            tp_price = round(live_price - tp_dist, 8)

        # ── الرافعة: أعلى رافعة متاحة لكل عملة (طلب المستخدم، يتحمّل المسؤولية) ──
        max_lev = client.get_max_leverage(inst_id)
        # فلتر: لا تدخل إلا العملات التي رافعتها القصوى > MIN_COIN_MAX_LEVERAGE (طلب المستخدم)
        _min_lev = getattr(cfg, "MIN_COIN_MAX_LEVERAGE", 0)
        if _min_lev and (not max_lev or max_lev <= _min_lev):
            add_log(status,
                f"⏭️ {inst_id}: رافعتها القصوى x{max_lev or 0} ≤ x{_min_lev} — تُخطّى. التالي",
                "info")
            continue
        if getattr(cfg, "USE_MAX_LEVERAGE", False):
            eff_leverage = float(max_lev) if max_lev else float(LEVERAGE)
        else:
            eff_leverage = float(LEVERAGE)
            if max_lev and max_lev < eff_leverage:
                eff_leverage = float(max_lev)
        # ── سقف حماية من التصفية: لا تصفية إلا بفجوة ≥ LIQ_GAP_BUFFER ──────────
        # التصفية ≈ عند حركة 1/الرافعة؛ نحدّ الرافعة بحيث تحتاج التصفية فجوة كبيرة.
        gap = getattr(cfg, "LIQ_GAP_BUFFER", 0.0)
        if gap and gap > 0:
            liq_safe_cap = 1.0 / gap
            if eff_leverage > liq_safe_cap:
                eff_leverage = liq_safe_cap
        eff_leverage = max(1, int(round(eff_leverage)))
        add_log(status,
            f"\U0001f3af {inst_id}: رافعة x{eff_leverage} | "
            f"SL {sl_move*100:.2f}% TP {tp_move*100:.2f}% | "
            f"⚡سرعة:{best.get('speed_score', 0)*100:.2f}% "
            f"💥انفجار:{best.get('explosion', 0):.1f}", "info")

        # رأس المال كاملاً موزّعاً على المراكز المتاحة — طلب المستخدم (2-3 عملات)
        # نقسم رأس المال الكامل على الخانات المتبقّية فيُملأ كل مركز بحصّة متساوية
        # عبر الدورات: خانة 1 = 1/3 من الحرّ، خانة 2 = 1/2 من المتبقّي، خانة 3 = الكل.
        slots_remaining = max(1, cfg.MAX_POSITIONS - len(active))
        alloc_ratio  = CAPITAL_RATIO / slots_remaining
        risk_capital = balance * alloc_ratio

        client.set_leverage(inst_id, eff_leverage)
        sz = client.calculate_contracts(inst_id, balance, live_price, eff_leverage, alloc_ratio)
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
                    f"\U0001f4e4 maker {direction} {inst_id} @~{live_price} x{eff_leverage} | "
                    f"درجة:{score} | رأس المال:${risk_capital:.3f} | SL:{sl_move*100:.2f}% TP:{tp_move*100:.2f}% (بانتظار التنفيذ)", "success")
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
                                    sl_move, tp_move,
                                    sl_override=sl_price, tp_override=tp_price)
        if result["code"] == "0":
            add_log(status,
                f"✅ {direction} {inst_id} @ {live_price} x{eff_leverage} | "
                f"درجة:{score} | رأس المال:${risk_capital:.3f} | SL:{sl_move*100:.2f}% TP:{tp_move*100:.2f}%", "success")
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
            # ⛔ حماية من التصفية: لا نفتح مركزاً بلا وقف خسارة أبداً.
            # المركز العاري عند رافعة عالية = تصفية مؤكّدة على أول حركة 1-2%.
            # نتخطّى العملة بدل المخاطرة. (أُزيل place_order_no_sltp بطلب «لا تتصفّى»)
            add_log(status,
                f"⏭️ {inst_id}: فشل وضع وقف الخسارة ({err_msg}) — "
                f"تُخطّى لمنع مركز عارٍ يُصفّى. التالي", "warning")


if __name__ == "__main__":
    asyncio.run(run())
