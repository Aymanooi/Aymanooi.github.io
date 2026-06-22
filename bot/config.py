TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

KLINE_INTERVAL = "60"  # hourly candles
KLINE_LIMIT = 100      # last 100 candles for indicators

MAX_POSITION_PCT = 0.15    # max 15% of balance per trade
MIN_CONFIDENCE = 70        # skip trades below this confidence
MIN_TRADE_USDT = 10        # minimum order size in USDT

ACCOUNT_TYPE = "CONTRACT"  # UNIFIED or CONTRACT for derivatives
