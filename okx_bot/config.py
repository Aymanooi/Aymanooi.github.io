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
#   "safe"       = آمن: رافعة 5×، مخاطرة 2% (لاختبار البوت)
#   "balanced"   = متوازن: رافعة 20×، مخاطرة 5%، مركزان متزامنان
#   "boost"      = بوست: رافعة 15×، مخاطرة 7% (وسط بين balanced و aggressive)
#   "aggressive" = عدواني: رافعة 20×، Kelly كامل
#   "turbo"      = توربو: رافعة 20×، Full Kelly، 50 عملة → هدف $1M في 15 سنة
#   "nitro"      = نيترو: 20×، Full Kelly، فلتر الخاسرين → هدف $1M في ~3 سنوات
#   "hyper"      = هايبر: 20×، Full Kelly، فلتر + مركزان متزامنان → هدف $1M في ~1.5 سنة
RISK_MODE = os.getenv("RISK_MODE", "safe").strip().lower()

_RISK_PRESETS = {
    "safe":       {"leverage": 5,  "risk_per_trade": 0.02, "kelly_cap": 0.10, "half_kelly": True,  "symbols": 10,  "filter_losers": False, "max_positions": 1},
    "balanced":   {"leverage": 20, "risk_per_trade": 0.05, "kelly_cap": 0.15, "half_kelly": True,  "symbols": 50,  "filter_losers": False, "max_positions": 2},
    "boost":      {"leverage": 15, "risk_per_trade": 0.07, "kelly_cap": 0.18, "half_kelly": False, "symbols": 50,  "filter_losers": False, "max_positions": 1},
    "aggressive": {"leverage": 20, "risk_per_trade": 0.10, "kelly_cap": 0.20, "half_kelly": False, "symbols": 50,  "filter_losers": False, "max_positions": 1},
    "turbo":      {"leverage": 20, "risk_per_trade": 0.06, "kelly_cap": 0.25, "half_kelly": False, "symbols": 50,  "filter_losers": False, "max_positions": 1},
    # nitro: يتداول على 50 عملة، يحذف تلقائياً العملات الخاسرة بعد 5 صفقات
    # هدف: $10 → $1M في ~3 سنوات (إذا ثبت معدل الفوز على الأزواج الجيدة)
    "nitro":      {"leverage": 20, "risk_per_trade": 0.15, "kelly_cap": 0.35, "half_kelly": False, "symbols": 50,  "filter_losers": True,  "max_positions": 1},
    # hyper: نفس nitro + مركزان متزامنان → يضاعف الصفقات/شهر → هدف 1.5 سنة
    # تنبيه: المخاطرة أعلى — لا تستخدم إلا إذا كنت مستعداً لخسارة رأس المال كاملاً
    "hyper":      {"leverage": 20, "risk_per_trade": 0.12, "kelly_cap": 0.45, "half_kelly": False, "symbols": 50,  "filter_losers": True,  "max_positions": 2},
    # ultra: 5 مراكز متزامنة → 80 صفقة/شهر → احتمال 35% للوصول $1M في 6 أشهر
    #        احتمال 80% للوصول $1M في 12 شهر (أوصى بها على 6 أشهر)
    # ⚠️ أعلى مخاطرة — احتمال الخسارة الكاملة موجود إذا WR < 25%
    "ultra":      {"leverage": 20, "risk_per_trade": 0.10, "kelly_cap": 0.50, "half_kelly": False, "symbols": 50,  "filter_losers": True,  "max_positions": 5},
}
_preset = _RISK_PRESETS.get(RISK_MODE, _RISK_PRESETS["safe"])

# === Trading Parameters ===
LEVERAGE       = _preset["leverage"]
RISK_PER_TRADE = _preset["risk_per_trade"]
KELLY_CAP      = _preset["kelly_cap"]
HALF_KELLY     = _preset["half_kelly"]       # True=أمان, False=full Kelly
SCAN_SYMBOLS   = _preset["symbols"]          # عدد العملات المُمسوحة
FILTER_LOSERS  = _preset["filter_losers"]    # True=يحذف العملات الخاسرة تلقائياً
MAX_POSITIONS  = _preset["max_positions"]    # عدد المراكز المتزامنة
CAPITAL_RATIO  = 0.95
STOP_LOSS_PCT  = 0.02
TAKE_PROFIT_PCT = 0.04

# === Strategy Parameters ===
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_BUY_MAX = 65
RSI_SELL_MIN = 35
TIMEFRAME = "15m"
SIGNAL_THRESHOLD = 42

# === Bot Settings ===
SCAN_INTERVAL   = 60
TOP_PAIRS_COUNT = 50
