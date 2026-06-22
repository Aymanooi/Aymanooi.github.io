# OKX Trading Bot - Configuration

# === API Credentials ===
API_KEY = ""
API_SECRET = ""
PASSPHRASE = ""

# === Mode ===
# "1" = Demo (paper trading) - ابدأ هنا دائماً
# "0" = Live (real money)
IS_DEMO = "1"

# === Trading Parameters ===
LEVERAGE = 20
CAPITAL_RATIO = 0.95       # 95% of balance per trade
STOP_LOSS_PCT = 0.02       # 2% stop loss
TAKE_PROFIT_PCT = 0.04     # 4% take profit

# === Strategy Parameters ===
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_BUY_MAX = 65
RSI_SELL_MIN = 35
TIMEFRAME = "15m"

# === Bot Settings ===
SCAN_INTERVAL = 60         # seconds between scans
TOP_PAIRS_COUNT = 50       # top N pairs by volume
MAX_POSITIONS = 1          # one trade at a time (full capital)
