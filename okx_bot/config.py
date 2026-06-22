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
#   "balanced"   = متوازن: رافعة 10×، مخاطرة 5%
#   "aggressive" = عدواني: رافعة 20×، Kelly كامل
#   "turbo"      = توربو: رافعة 20×، Full Kelly، 50 عملة → هدف $1M في 15 سنة
RISK_MODE = os.getenv("RISK_MODE", "safe").strip().lower()

_RISK_PRESETS = {
    "safe":       {"leverage": 5,  "risk_per_trade": 0.02, "kelly_cap": 0.10, "half_kelly": True,  "symbols": 10},
    "balanced":   {"leverage": 10, "risk_per_trade": 0.05, "kelly_cap": 0.15, "half_kelly": True,  "symbols": 25},
    "aggressive": {"leverage": 20, "risk_per_trade": 0.10, "kelly_cap": 0.20, "half_kelly": False, "symbols": 50},
    "turbo":      {"leverage": 20, "risk_per_trade": 0.06, "kelly_cap": 0.25, "half_kelly": False, "symbols": 50},
}
_preset = _RISK_PRESETS.get(RISK_MODE, _RISK_PRESETS["safe"])

# === Trading Parameters ===
LEVERAGE = _preset["leverage"]
RISK_PER_TRADE = _preset["risk_per_trade"]
KELLY_CAP = _preset["kelly_cap"]
HALF_KELLY = _preset["half_kelly"]      # True=أمان, False=full Kelly
SCAN_SYMBOLS = _preset["symbols"]       # عدد العملات المُمسوحة
CAPITAL_RATIO = 0.95
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
SCAN_INTERVAL = 60
TOP_PAIRS_COUNT = 50
MAX_POSITIONS = 1
