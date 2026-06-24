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
    # rocket: الإعداد الأقل سوءاً المُثبَت بالبحث على بيانات OKX حقيقية (مصفوفة 30 تركيبة).
    # الوقف الضيّق 0.5% + x20 + رأس مال كامل = الزاوية الأسوأ (PF 0.58، تصفية 100%).
    # الأفضل تجريبياً: SL 2% / TP 4% / رافعة x3 / حجم مخفّض 20% → PF≈1.07، نجاة من سلسلة الخسائر.
    # ⚠️ الحافة هزيلة (قد تكون ضمن ضجيج الباكتيست) — يجب التحقّق أماميّاً على Demo قبل الثقة.
    "rocket":     {"leverage": 3,  "risk_per_trade": 0.20, "kelly_cap": 0.20, "half_kelly": False, "symbols": 100, "filter_losers": True,  "max_positions": 1},
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
STOP_LOSS_PCT   = 0.02    # وقف الخسارة: 2% — أوسع من ضجيج السوق (الباكتيست: 0.5% أسوأ بكثير)
TAKE_PROFIT_PCT = 0.04    # هدف الربح: 4% — نسبة مخاطرة:عائد 2:1 (أفضل PF تجريبياً)

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
TIMEFRAME = "15m"
SIGNAL_THRESHOLD = 55   # رُفِعت 35→55: انتقائية قصوى — أقوى الإشارات فقط، رسوم أقل، نزيف أبطأ

# === Bot Settings ===
SCAN_INTERVAL   = 60
TOP_PAIRS_COUNT = 100
