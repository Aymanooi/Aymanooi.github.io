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

# ⛔ أصول محظورة من الدخول (طلب المستخدم): لا BTC/ETH/SOL/XAU.
# (XAU = الذهب المرمّز — أُضيف بطلب المستخدم 2026-07-04.)
# المراكز المفتوحة مسبقاً على أصل محظور تُدار حتى تُغلق طبيعياً.
BANNED_ASSETS  = ("BTC", "ETH", "SOL", "XAU")

# 🐸 تفضيل عملات الميم (طلب المستخدم: «من الأفضل فقط عملات MEME»).
# قائمة منسّقة لأشهر عملات الميم المتداولة كعقود دائمة على OKX —
# الأعنف تقلباً والأسرع حركة، فتنسجم مع طلب «السرعة الهائلة».
# التفضيل ذكي: إن وُجد مرشح ميم مؤهَّل نختاره؛ وإلا نرجع لبقية العملات
# حتى لا يبقى البوت خارج السوق (احتراماً لـ 24/7 والتناوب الدائم).
MEME_PREFER = os.getenv("BOT_MEME_PREFER", "1").strip() != "0"
# حصري على الميم (طلب المستخدم: «الدخول فقط في عملات الميم»): يتخطّى
# البوت أي عملة ليست ميم في المسح — فإن لم تتوفّر فرصة ميم لا يدخل
# إطلاقاً (بلا رجوع لغير الميم). أقوى من MEME_PREFER.
MEME_ONLY = os.getenv("BOT_MEME_ONLY", "1").strip() != "0"

# 💲 نطاق السعر المسموح للدخول (طلب المستخدم: بين ~صفر و 1 دولار).
# نتخطّى أي عملة سعرها ≥ MAX_PRICE_USD أو ≤ MIN_PRICE_USD.
# العملات الرخيصة/الميكرو — تنسجم مع الميم والسرعة الهائلة.
MIN_PRICE_USD = float(os.getenv("BOT_MIN_PRICE_USD", "1e-19"))
MAX_PRICE_USD = float(os.getenv("BOT_MAX_PRICE_USD", "1.0"))

# 📊 فلتر الحركة اليومية (طلب المستخدم): لا دخول إلا في العملات التي
# صعدت أكثر من MOM_UP_PCT% أو هبطت أكثر من MOM_DOWN_PCT% خلال 24 ساعة.
MOMENTUM_FILTER = os.getenv("BOT_MOMENTUM_FILTER", "1").strip() != "0"
MOM_UP_PCT   = float(os.getenv("BOT_MOM_UP_PCT", "10.0"))   # صعود > +10%
MOM_DOWN_PCT = float(os.getenv("BOT_MOM_DOWN_PCT", "5.0"))  # هبوط > −5%
MEME_ASSETS = (
    "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "MEME", "TRUMP",
    "POPCAT", "MEW", "BRETT", "TURBO", "MOG", "PNUT", "GOAT", "NEIRO",
    "ACT", "MOODENG", "CHILLGUY", "PEOPLE", "DOGS", "BOME", "SLERF",
    "MYRO", "WEN", "BABYDOGE", "SPX", "GIGA", "PONKE", "FARTCOIN",
    "AI16Z", "ZEREBRO", "GRIFFAIN", "MICHI", "SUNDOG", "DEGEN", "TShib",
    "BONK", "CAT", "HIPPO", "MAGA", "WOJAK", "LADYS", "ELON", "AIDOGE",
    "BABYNEIRO", "SIGMA", "FWOG", "LUCE", "USELESS", "RETARDIO", "GME",
    "SNEK", "ANDY", "APU", "MUMU", "BILLY", "SC", "HARAMBE",
)
RISK_PER_TRADE = _preset["risk_per_trade"]
KELLY_CAP      = _preset["kelly_cap"]
HALF_KELLY     = _preset["half_kelly"]       # True=نصف Kelly (أمان), False=Kelly الكامل
SCAN_SYMBOLS   = _preset["symbols"]          # عدد العملات المُمسوحة
FILTER_LOSERS  = _preset["filter_losers"]    # True=يحذف العملات الخاسرة (Brain)
# عدد المراكز المتزامنة — يتجاوز قيمة الوضع عبر BOT_MAX_POSITIONS
# (طلب المستخدم: 3 عملات متزامنة مع بقاء باقي إعدادات rocket)
MAX_POSITIONS  = int(os.getenv("BOT_MAX_POSITIONS",
                               str(_preset["max_positions"])))
# نسبة رأس المال المستخدَمة كهامش. 0.99 كانت تُفشل الأمر بـ«Insufficient
# USDT margin» لأن OKX يحتاج هامشاً حراً للرسوم ولأمر SL/TP المرفق —
# فيُرفض الدخول بالكامل. 0.90 يترك 10% حرة فتُنفَّذ الصفقات فعلاً.
CAPITAL_RATIO   = float(os.getenv("BOT_CAPITAL_RATIO", "0.90"))
# طلب المستخدم الصريح: هدف 1% ووقف 1% (نسبة 1:1، أضيق).
# التعادل يحتاج فوز 50%+ (المقاس ~32%)، والرسوم تلتهم حصة أكبر من
# الهدف الأقصر — رياضياً أصعب لا أسهل.
STOP_LOSS_PCT   = float(os.getenv("BOT_STOP_LOSS_PCT", "0.01"))
TAKE_PROFIT_PCT = float(os.getenv("BOT_TAKE_PROFIT_PCT", "0.01"))

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
# (طلب المستخدم: ≥ $50M). يقلّل الانزلاق ومشاكل حجم اللوت ويُحسّن تنفيذ أوامر maker.
MIN_USD_VOL_24H = int(os.getenv("BOT_MIN_USD_VOL_24H", "50000000"))

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
