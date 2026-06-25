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
    # rocket: إعداد المستخدم الصريح — رأس مال كامل، عملة واحدة، SL 0.5%، TP 1%، x20.
    # إعادة دخول فوري (30 ثانية). ⚠️ الباكتيست أثبت أنه عالي الخطورة (قد يُصفّي الحساب
    # عند سلسلة خسائر) — منفَّذ بطلب المستخدم الصريح المتكرر بعد إطلاعه الكامل على الأرقام.
    "rocket":     {"leverage": 20, "risk_per_trade": 1.0,  "kelly_cap": 1.0,  "half_kelly": False, "symbols": 100, "filter_losers": True,  "max_positions": 1},
}
_preset = _RISK_PRESETS.get(RISK_MODE, _RISK_PRESETS["safe"])

# === Trading Parameters ===
LEVERAGE       = _preset["leverage"]
RISK_PER_TRADE = _preset["risk_per_trade"]
KELLY_CAP      = _preset["kelly_cap"]
HALF_KELLY     = _preset["half_kelly"]       # True=نصف Kelly (أمان), False=Kelly الكامل
SCAN_SYMBOLS   = _preset["symbols"]          # عدد العملات المُمسوحة
FILTER_LOSERS  = _preset["filter_losers"]    # True=يحذف العملات الخاسرة (Brain)
MAX_POSITIONS  = _preset["max_positions"]    # عدد المراكز المتزامنة
CAPITAL_RATIO   = 0.95
STOP_LOSS_PCT   = 0.005   # احتياط فقط (يُستخدم إن تعذّر حساب ATR)
TAKE_PROFIT_PCT = 0.01    # احتياط فقط (يُستخدم إن تعذّر حساب ATR)

# === Variable (Adaptive) Risk — طلب المستخدم: رافعة/وقف/هدف متغيّرة حسب العملة ===
# بدل القيم الثابتة، يُفصَّل كل شيء على تقلّب العملة نفسها (ATR):
#   • وقف الخسارة = ATR_SL_MULT × ATR  (يتّسع للعملة المتذبذبة، يضيق للهادئة)
#   • الهدف        = ATR_TP_MULT × ATR  (RR=3:1 → التعادل عند فوز 25% فقط بدل 66%+)
#   • الرافعة      = تُحسب لكل عملة لتثبيت خسارة الهامش عند SL عند TARGET_SL_MARGIN،
#                    مُقيَّدة بين LEV_MIN وسقف المستخدم LEVERAGE (x20) وحدّ العملة.
# هذا أفضل رياضياً من الإعداد الثابت 0.5%/1%: نسبة الربح/الخسارة 3:1 تخفض نسبة
# الفوز المطلوبة للتعادل من ~66% إلى 25%، وتثبيت مخاطرة كل صفقة يحمي من التصفية.
VARIABLE_RISK    = True
ATR_SL_MULT      = 1.5    # مضاعف وقف الخسارة (×ATR)
ATR_TP_MULT      = 4.5    # مضاعف الهدف (×ATR) → نسبة ربح/خسارة 3:1
TARGET_SL_MARGIN = 0.18   # خسارة الهامش المستهدفة عند ضرب SL (تُثبَّت عبر الرافعة)
LEV_MIN          = 3      # أدنى رافعة للعملة شديدة التذبذب
LEV_MAX          = LEVERAGE   # سقف الرافعة = اختيار المستخدم (x20)

# === Order Mode ===
# "maker" = أوامر حدّية post-only تحذف رسوم taker (~2% على x20) — الباكتيست أثبت
#           أنها تضاعف الحافة الصافية ($10→$24.86 مقابل $10.67). السلبية: قد لا
#           يُنفَّذ الأمر لو ابتعد السعر، فيُنظَّف ويُعاد في الدورة التالية.
# "taker" = أوامر سوق فورية التنفيذ لكن برسوم أعلى (ارجع إليها لو ضعُف معدّل التنفيذ).
ORDER_MODE   = os.getenv("ORDER_MODE", "maker").strip().lower()
MAKER_OFFSET = float(os.getenv("MAKER_OFFSET", "0.0005"))   # إزاحة سعر الـmaker (0.05%)

# === Strategy Parameters ===
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_BUY_MAX = 65
RSI_SELL_MIN = 35
TIMEFRAME = "1m"   # سكالبينغ فريم الدقيقة (طلب المستخدم)
SIGNAL_THRESHOLD = 35   # عتبة الدخول المتكرر — تتيح الدخول السريع المتتالي (طلب المستخدم)

# === Bot Settings ===
SCAN_INTERVAL   = 60
TOP_PAIRS_COUNT = 100
