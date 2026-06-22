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
#   "safe"       = آمن: رافعة 5×، مخاطرة 2% لكل صفقة (موصى به للبدء)
#   "balanced"   = متوازن: رافعة 10×، مخاطرة 5%
#   "aggressive" = عدواني: رافعة 20×، مخاطرة Kelly كامل (خطر تصفية الحساب)
RISK_MODE = os.getenv("RISK_MODE", "safe").strip().lower()

_RISK_PRESETS = {
    "safe":       {"leverage": 5,  "risk_per_trade": 0.02, "kelly_cap": 0.10},
    "balanced":   {"leverage": 10, "risk_per_trade": 0.05, "kelly_cap": 0.15},
    "aggressive": {"leverage": 20, "risk_per_trade": 0.10, "kelly_cap": 0.20},
}
_preset = _RISK_PRESETS.get(RISK_MODE, _RISK_PRESETS["safe"])

# === Trading Parameters ===
LEVERAGE = _preset["leverage"]
RISK_PER_TRADE = _preset["risk_per_trade"]   # حد المخاطرة من رأس المال لكل صفقة
KELLY_CAP = _preset["kelly_cap"]             # سقف نسبة Kelly
CAPITAL_RATIO = 0.95       # 95% of balance per trade (للوضع العدواني فقط)
STOP_LOSS_PCT = 0.02       # 2% stop loss
TAKE_PROFIT_PCT = 0.04     # 4% take profit

# === Strategy Parameters ===
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_BUY_MAX = 65
RSI_SELL_MIN = 35
TIMEFRAME = "15m"
SIGNAL_THRESHOLD = 42      # عتبة الإشارة (جودة أعلى = صفقات أقل وأدق)

# === Bot Settings ===
SCAN_INTERVAL = 60         # seconds between scans
TOP_PAIRS_COUNT = 50       # top N pairs by volume
MAX_POSITIONS = 1          # one trade at a time (full capital)
