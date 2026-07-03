# OKX Trading Bot - Configuration
import os

# === API Credentials ===
API_KEY = ""
API_SECRET = ""
PASSPHRASE = ""

# === Mode ===
# "1" = Demo (paper trading) - ابدأ هنا دائماً
# "0" = Live (real money)
IS_DEMO = "1"

# === Risk Mode ===
# يُضبط بمتغيّر البيئة RISK_MODE في GitHub Secrets:
#   "safe"    = آمن: رافعة 5×، مخاطرة 2%، 1 مركز
#   "balanced"= متوازن: رافعة 20×، مخاطرة 5%، 3 مراكز
#   "boost"   = بوست: رافعة 15×، مخاطرة 7%
#   "nitro"   = نيترو: رافعة 20×، مخاطرة 15%، فلتر الخاسرين
#   "hyper"   = هايبر: رافعة 20×، مخاطرة 12%، 2 مراكز + فلتر
#   "ultra"   = ألترا: رافعة 20×، مخاطرة 10%، 5 مراكز + فلتر
#   "rocket"  = روكيت: الإعداد الأقل سوءاً تجريبياً — x3، SL 2%، TP 4%، حجم 20%، عملة واحدة
RISK_MODE = os.getenv("RISK_MODE", "rocket").strip().lower()

_RISK_PRESETS = {
    "safe":       {"leverage": 5,  "risk_per_trade": 0.02, "kelly_cap": 0.10, "half_kelly": True,  "symbols": 10,  "filter_losers": False, "max_positions": 1},
    "balanced":   {"leverage": 20, "risk_per_trade": 0.05, "kelly_cap": 0.25, "half_kelly": False, "symbols": 100, "filter_losers": False, "max_positions": 3},
    "boost":      {"leverage": 15, "risk_per_trade": 0.07, "kelly_cap": 0.18, "half_kelly": False, "symbols": 50,  "filter_losers": False, "max_positions": 1},
    "aggressive": {"leverage": 20, "risk_per_trade": 0.10, "kelly_cap": 0.20, "half_kelly": False, "symbols": 50,  "filter_losers": False, "max_positions": 1},
    "turbo":      {"leverage": 20, "risk_per_trade": 0.06, "kelly_cap": 0.25, "half_kelly": False, "symbols": 50,  "filter_losers": False, "max_positions": 1},
    "nitro":      {"leverage": 20, "risk_per_trade": 0.15, "kelly_cap": 0.35, "half_kelly": False, "symbols": 50,  "filter_losers": True,  "max_positions": 1},
    "hyper":      {"leverage": 20, "risk_per_trade": 0.12, "kelly_cap": 0.45, "half_kelly": False, "symbols": 50,  "filter_losers": True,  "max_positions": 2},
    "ultra":      {"leverage": 20, "risk_per_trade": 0.10, "kelly_cap": 0.50, "half_kelly": False, "symbols": 50,  "filter_losers": True,  "max_positions": 5},
    # compound: أفضل إعداد أثبت PF>1 على بيانات OKX الحقيقية (2025-06):
    # x2 / SL 4% / TP 2% → فوز 68.9% / PF=1.06 / مخاطرة 5% لكل صفقة.
    # رياضيات التراكم المركّب: $8 → $1M في ~870 يوم (100 صفقة/يوم، 5% مخاطرة).
    # مخاطرة 5% (بدل رأس المال الكامل) = التراكم يعمل لصالحك لا ضدّك.
    "rocket":     {"leverage": 25,  "risk_per_trade": 0.05, "kelly_cap": 0.10, "half_kelly": True,  "symbols": 100, "filter_losers": True,  "max_positions": 1},
    # prime: تجميع كل ما أثبت PF>1 في بيانات هذا المستودع الحقيقية في
    # إعداد واحد: رافعة x3 (الحافة المثلى على فريم الدقيقة، PF=1.07)
    # مع مخارج compound (SL 4% / TP 2% → فوز 68.9%، PF=1.06) وفلتر
    # الخاسرين. يعمل مع فلاتر تأكيد الأطر كاملة (PF 1.38→1.69 خارج
    # العيّنة) — أي بدون تناوب إجباري.
    "prime":      {"leverage": 3,  "risk_per_trade": 0.05, "kelly_cap": 0.10, "half_kelly": True,  "symbols": 100, "filter_losers": True,  "max_positions": 3},
}
_preset = _RISK_PRESETS.get(RISK_MODE, _RISK_PRESETS["safe"])

# === Trading Parameters ===
# الرافعة — تتجاوز قيمة الوضع عبر BOT_LEVERAGE (طلب المستخدم: x5)
LEVERAGE       = int(os.getenv("BOT_LEVERAGE", str(_preset["leverage"])))

# ⛔ أصول محظورة من الدخول (طلب المستخدم): لا BTC ولا ETH ولا SOL.
# المراكز المفتوحة مسبقاً على أصل محظور تُدار حتى تُغلق طبيعياً.
BANNED_ASSETS  = ("BTC", "ETH", "SOL")
RISK_PER_TRADE = _preset["risk_per_trade"]
KELLY_CAP      = _preset["kelly_cap"]
HALF_KELLY     = _preset["half_kelly"]       # True=نصف Kelly (أمان), False=Kelly الكامل
SCAN_SYMBOLS   = _preset["symbols"]          # عدد العملات المُمسوحة
FILTER_LOSERS  = _preset["filter_losers"]    # True=يحذف العملات الخاسرة (Brain)
# عدد المراكز المتزامنة — يتجاوز قيمة الوضع عبر BOT_MAX_POSITIONS
# (طلب المستخدم: 3 عملات متزامنة مع بقاء باقي إعدادات rocket)
MAX_POSITIONS  = int(os.getenv("BOT_MAX_POSITIONS",
                               str(_preset["max_positions"])))
CAPITAL_RATIO   = 0.99    # رأس المال الكامل — 99% هامش (1% محجوز لرسم الفتح فقط، وإلا OKX يرفض الأمر كله)
# طلب المستخدم الصريح: هدف 2% ووقف 2% (نسبة 1:1 متماثلة).
# الهدف الأقرب يُصاب أسرع وأكثر تكراراً — لكن التعادل يحتاج فوز 50%+.
STOP_LOSS_PCT   = 0.02
TAKE_PROFIT_PCT = 0.02

# === أعلى رافعة لكل عملة (طلب المستخدم الصريح — يتحمّل المسؤولية الكاملة) ===
# True = استخدم أقصى رافعة تتيحها OKX لكل عملة (قد تبلغ x50-x100).
# تحذير موثّق بالبيانات: هذا حوّل $2.62 إلى $0.21 في الباكتيست (تصفية).
# False = رافعة الوضع الثابتة (البوت القديم: x20 في balanced) بدل أقصى
# رافعة لكل عملة — طلب المستخدم إعادة البوت القديم (2026-07-03)
USE_MAX_LEVERAGE = False

# لا تدخل إلا العملات التي رافعتها القصوى أكبر من هذه القيمة (طلب المستخدم: > x40)
MIN_COIN_MAX_LEVERAGE = 0   # معطّل — الإعداد الرابح يتداول كل العملات السائلة

# === حماية من التصفية ===
# 0.0 = معطّل (رافعة قصوى حقيقية بلا سقف).
# قيمة موجبة (مثل 0.06) تسقُف الرافعة فتمنع التصفية إلا بفجوة بهذا الحجم.
# ⚠️ بـ 0.0: أقصى رافعة (x50-100) تُعيد خطر التصفية على حركة 1-2%.
# 0.0333 = سقف فعلي x30 (لا تصفية إلا بفجوة سعرية ≥ 3.33%) — يسمح
# برافعة x30 المطلوبة ويبقى مانعاً للقفز إلى x50-100.
# ⚠️ عند x30: التصفية تقع على حركة معاكسة ~3.3% فقط.
LIQ_GAP_BUFFER = 0.0333

# === Variable Risk — معطَّل ===
VARIABLE_RISK    = False
ATR_SL_MULT      = 1.5
ATR_TP_MULT      = 3.0
TARGET_SL_MARGIN = 0.18
LEV_MIN          = 2
LEV_MAX          = LEVERAGE

# === Order Mode ===
# "maker" = أوامر حدّية post-only تحذف رسوم taker (~2% على x20) — الباكتيست أثبت
#           أنها تضاعف الحافة الصافية ($10→$24.86 مقابل $10.67). السلبية: قد لا
#           يُنفَّذ الأمر لو ابتعد السعر، فيُنظَّف ويُعاد في الدورة التالية.
# "taker" = أوامر سوق فورية التنفيذ لكن برسوم أعلى (ارجع إليها لو ضعُف معدّل التنفيذ).
ORDER_MODE   = os.getenv("ORDER_MODE", "maker").strip().lower()  # maker: رسوم أقل (PF 0.87→1.0+)
MAKER_OFFSET = float(os.getenv("MAKER_OFFSET", "0.0005"))   # إزاحة سعر الـmaker (0.05%)

# === Strategy Parameters ===
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_BUY_MAX = 65
RSI_SELL_MIN = 35
TIMEFRAME = "1m"  # فريم الدقيقة — الحافة المثلى عند x3 (PF=1.07 بالباكتيست)
SIGNAL_THRESHOLD = 35   # عتبة الدخول المتكرر — تتيح الدخول السريع المتتالي (طلب المستخدم)

# === Bot Settings ===
SCAN_INTERVAL   = 60
TOP_PAIRS_COUNT = 100
# الحدّ الأدنى للسيولة بالدولار خلال 24 ساعة — لا دخول إلا في العملات الأعلى سيولة
# (طلب المستخدم: ≥ $10M). يقلّل الانزلاق ومشاكل حجم اللوت ويُحسّن تنفيذ أوامر maker.
MIN_USD_VOL_24H = 80_000_000

# === بوّابة النظام التكيّفية (Regime Gate) — أثبت الباكتيست أنها ترفع PF 1.03→1.08 ===
REGIME_GATE   = True    # أوقِف الدخول في النوافذ الخاسرة، استأنف في الرابحة
REGIME_WINDOW = 8       # تقيس آخر 8 صفقات مغلقة
REGIME_MIN_WR = 0.40    # لو فوزها < 40% → توقّف مؤقت
REGIME_MAX_AGE= 600     # 10 دقائق — لا تُحتجز البوّابة بصفقات قديمة من إعداد مهجور

# === تأكيد الإطار الأعلى (HTF Confirmation) — أقوى استراتيجية مُختبَرة ===
# لا دخول إلا إذا اتّفق اتجاه 5m مع إشارة 1m. الباكتيست: PF 1.09→1.29، +39%.
HTF_CONFIRM = True
# تأكيد ثلاثي الأطر: 15m أيضاً يتّفق مع 1m+5m. الباكتيست: PF 1.28→1.49، +30%.
HTF_15M_CONFIRM = True
# تأكيد رباعي: 1H أيضاً يتّفق (1m+5m+15m+1H). صمد خارج العيّنة: PF 1.38→1.69، ضِعف.
HTF_1H_CONFIRM = True
# تأكيد Stochastic: لا دخول والمؤشّر مُنهَك (>80 شراء، <20 بيع). الباكتيست: PF 1.49→2.09.
STOCH_CONFIRM = False  # أُزيل: كان مُفرَط التخصيص (خارج العيّنة يضرّ ويقلّل الصفقات)
# RSI معتدل: لا دخول عند RSI متطرّف (شراء 40-68، بيع 32-60). صمد خارج العيّنة: PF 1.17→1.30.
RSI_MODERATE = True
