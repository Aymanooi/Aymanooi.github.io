"""OKX Futures Trading Bot — advanced starter (نسخة المالك، مُصلحة ومقيّدة)

بوت المستخدم الرابع — الأنضج تصميمًا بين المرفوعات:
  • رافعة تكيّفية مسوّرة (1-8x) تنخفض مع التقلب وترتفع مع قوة الإشارة
  • حارس تراجع يومي + حدّ خسائر متتالية + حدّ أدنى لحجم الأمر
  • Paper Trading و Demo افتراضيان، إعدادات كاملة عبر البيئة

إصلاحات على النسخة الملصوقة:
  • from __future__ / __main__ (فُقدت في النسخ)
  • إعادة بناء المسافات البادئة المفقودة

قيد المالك: ⛔ BTC / ETH / SOL محظورة برمجيًا — العملات البديلة فقط.
الافتراضي: XRP/USDT:USDT (بدّل عبر BOT_SYMBOL).

This is not a profit guarantee. It is a robust technical foundation.
"""
from __future__ import annotations

import os
import time
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import ccxt
import pandas as pd

# ============================
# Environment / Config
# ============================

SYMBOL = os.getenv("BOT_SYMBOL", "XRP/USDT:USDT")   # ⛔ بدون BTC/ETH/SOL
BANNED_ASSETS = ("BTC", "ETH", "SOL")               # قيد المالك — لا يُتجاوز

# وضع GitHub Actions: دورة واحدة عبر عدة عملات ثم خروج (بدل while True)
RUN_ONCE = os.getenv("BOT_RUN_ONCE", "false").lower() == "true"
SYMBOLS = [s.strip() for s in os.getenv(
    "BOT_SYMBOLS",
    "XRP/USDT:USDT,DOGE/USDT:USDT,ADA/USDT:USDT,"
    "AVAX/USDT:USDT,LINK/USDT:USDT,BNB/USDT:USDT").split(",") if s.strip()]

TIMEFRAME = os.getenv("BOT_TIMEFRAME", "5m")
LOOKBACK = int(os.getenv("BOT_LOOKBACK", "250"))
POLL_SECONDS = int(os.getenv("BOT_POLL_SECONDS", "60"))
PAPER_TRADING = os.getenv("BOT_PAPER_TRADING", "true").lower() == "true"
OKX_DEMO = os.getenv("OKX_DEMO", "true").lower() == "true"

BASE_LEVERAGE = int(os.getenv("BOT_BASE_LEVERAGE", "3"))
MAX_LEVERAGE = int(os.getenv("BOT_MAX_LEVERAGE", "8"))
MIN_LEVERAGE = int(os.getenv("BOT_MIN_LEVERAGE", "1"))
RISK_PER_TRADE = float(os.getenv("BOT_RISK_PER_TRADE", "0.01"))
MAX_DAILY_DRAWDOWN = float(os.getenv("BOT_MAX_DAILY_DRAWDOWN", "0.05"))
MAX_CONSECUTIVE_LOSSES = int(os.getenv("BOT_MAX_CONSECUTIVE_LOSSES", "4"))
MIN_USDT_ORDER = float(os.getenv("BOT_MIN_USDT_ORDER", "5"))

ATR_PERIOD = int(os.getenv("BOT_ATR_PERIOD", "14"))
EMA_FAST = int(os.getenv("BOT_EMA_FAST", "9"))
EMA_SLOW = int(os.getenv("BOT_EMA_SLOW", "21"))
EMA_TREND = int(os.getenv("BOT_EMA_TREND", "55"))
RSI_PERIOD = int(os.getenv("BOT_RSI_PERIOD", "14"))
ATR_MULT_SL = float(os.getenv("BOT_ATR_MULT_SL", "1.5"))
RR_TP = float(os.getenv("BOT_RR_TP", "2.0"))

API_KEY = os.getenv("OKX_API_KEY", "")
API_SECRET = os.getenv("OKX_API_SECRET", "")
API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE", "")

LOG_FILE = os.getenv("BOT_LOG_FILE", "okx_futures_bot.log")

# ============================
# Logging
# ============================

logger = logging.getLogger("okx-futures-bot")
logger.setLevel(logging.INFO)
_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

_sh = logging.StreamHandler()
_sh.setFormatter(_formatter)
logger.addHandler(_sh)

_fh = logging.FileHandler(LOG_FILE)
_fh.setFormatter(_formatter)
logger.addHandler(_fh)

# ============================
# Data models
# ============================


@dataclass
class Signal:
    side: str  # buy | sell
    entry: float
    stop_loss: float
    take_profit: float
    strength: float
    regime: str
    leverage: int


@dataclass
class BotState:
    equity_start_day: float = 0.0
    consecutive_losses: int = 0
    trading_enabled: bool = True
    last_signal_ts: Optional[pd.Timestamp] = None


# ============================
# Exchange
# ============================


def build_exchange() -> ccxt.okx:
    ex = ccxt.okx(
        {
            "apiKey": API_KEY,
            "secret": API_SECRET,
            "password": API_PASSPHRASE,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
    )
    if OKX_DEMO:
        ex.headers = {"x-simulated-trading": "1"}
    # دعم شهادة CA مخصصة (بيئات خلف بروكسي شركات/تطوير)
    # ملاحظة: ccxt يحسب (verify and validateServerSsl) — يجب ضبط الاثنين
    # حتى يصل مسار الشهادة فعليًا إلى requests
    ca_bundle = os.getenv("BOT_CA_BUNDLE", "")
    if ca_bundle:
        ex.verify = ca_bundle
        ex.validateServerSsl = ca_bundle
        ex.session.verify = ca_bundle
    return ex


# ============================
# Indicators
# ============================


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"].replace(0, pd.NA)
    return (tp * vol).cumsum() / vol.cumsum()


# ============================
# Data
# ============================


def fetch_ohlcv_df(exchange: ccxt.okx, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


# ============================
# Regime detection
# ============================


def detect_regime(df: pd.DataFrame) -> str:
    last = df.iloc[-1]
    atr_pct = float(last["atr"] / last["close"]) if last["close"] else 0.0
    trend_gap = abs(float(last["ema_fast"] - last["ema_slow"])) / float(last["close"])

    if atr_pct > 0.01 and trend_gap > 0.002:
        return "trending"
    if atr_pct > 0.02:
        return "volatile"
    return "ranging"


# ============================
# Strategy engine
# ============================


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = ema(out["close"], EMA_FAST)
    out["ema_slow"] = ema(out["close"], EMA_SLOW)
    out["ema_trend"] = ema(out["close"], EMA_TREND)
    out["rsi"] = rsi(out["close"], RSI_PERIOD)
    out["atr"] = atr(out, ATR_PERIOD)
    out["vwap"] = vwap(out)
    out["vol_ma"] = out["volume"].rolling(20).mean()
    return out


def adaptive_leverage(regime: str, atr_pct: float, strength: float) -> int:
    # Higher uncertainty -> lower leverage
    if regime == "volatile":
        lev = MIN_LEVERAGE + 1
    elif regime == "trending":
        lev = BASE_LEVERAGE + 1
    else:
        lev = BASE_LEVERAGE

    if atr_pct > 0.015:
        lev -= 1
    if strength > 0.65:
        lev += 1

    return int(max(MIN_LEVERAGE, min(MAX_LEVERAGE, lev)))


def generate_signal(df: pd.DataFrame) -> Optional[Signal]:
    if len(df) < max(EMA_TREND, 60):
        return None

    df = compute_features(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if pd.isna(last["atr"]) or pd.isna(last["rsi"]) or pd.isna(last["vwap"]):
        return None

    regime = detect_regime(df)

    bullish_cross = prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"]
    bearish_cross = prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"]

    price = float(last["close"])
    atr_value = float(last["atr"])
    atr_pct = atr_value / price if price else 0.0
    stop_dist = max(atr_value * ATR_MULT_SL, price * 0.002)

    volume_ok = float(last["volume"]) > float(last["vol_ma"]) if not pd.isna(last["vol_ma"]) else True
    trend_bull = last["close"] > last["ema_trend"]
    trend_bear = last["close"] < last["ema_trend"]

    # Long
    if bullish_cross and last["rsi"] > 50 and trend_bull and price > last["vwap"] and volume_ok:
        strength = float(min(1.0, ((last["rsi"] - 50) / 50) + max(0.0, (price - last["ema_trend"]) / price)))
        lev = adaptive_leverage(regime, atr_pct, strength)
        sl = price - stop_dist
        tp = price + stop_dist * RR_TP
        return Signal("buy", price, sl, tp, strength, regime, lev)

    # Short
    if bearish_cross and last["rsi"] < 50 and trend_bear and price < last["vwap"] and volume_ok:
        strength = float(min(1.0, ((50 - last["rsi"]) / 50) + max(0.0, (last["ema_trend"] - price) / price)))
        lev = adaptive_leverage(regime, atr_pct, strength)
        sl = price + stop_dist
        tp = price - stop_dist * RR_TP
        return Signal("sell", price, sl, tp, strength, regime, lev)

    return None


# ============================
# Risk controls
# ============================


def get_equity_usdt(exchange: ccxt.okx) -> float:
    try:
        bal = exchange.fetch_balance()
        total = bal.get("total", {}) or {}
        free = bal.get("free", {}) or {}
        return float(total.get("USDT") or free.get("USDT") or 0.0)
    except Exception as e:
        logger.warning(f"Balance fetch failed: {e}")
        return 0.0


def get_open_position(exchange: ccxt.okx, symbol: str) -> Dict[str, Any]:
    try:
        positions = exchange.fetch_positions([symbol])
        for p in positions:
            contracts = float(p.get("contracts") or 0.0)
            if contracts != 0:
                return p
    except Exception as e:
        logger.warning(f"Position fetch failed: {e}")
    return {}


def position_size(equity: float, entry: float, stop_loss: float, leverage: int) -> float:
    risk_usdt = equity * RISK_PER_TRADE
    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        return 0.0

    qty_by_risk = risk_usdt / stop_distance
    qty_by_leverage = (equity * leverage) / entry
    qty = min(qty_by_risk, qty_by_leverage)

    if qty * entry < MIN_USDT_ORDER:
        return 0.0
    return float(qty)


def daily_drawdown_guard(state: BotState, equity_now: float) -> bool:
    if state.equity_start_day <= 0:
        state.equity_start_day = equity_now
        return True
    dd = (state.equity_start_day - equity_now) / state.equity_start_day
    return dd < MAX_DAILY_DRAWDOWN


# ============================
# Execution
# ============================


def set_leverage(exchange: ccxt.okx, symbol: str, leverage: int) -> None:
    try:
        exchange.set_leverage(leverage, symbol)
        logger.info(f"Leverage set to {leverage}x on {symbol}")
    except Exception as e:
        logger.warning(f"Could not set leverage: {e}")


def submit_order(exchange: ccxt.okx, symbol: str, signal: Signal, qty: float) -> None:
    if qty <= 0:
        logger.info("Qty too small, skipping.")
        return

    side = signal.side
    exit_side = "sell" if side == "buy" else "buy"

    if PAPER_TRADING:
        logger.info(
            f"[PAPER] {side.upper()} {symbol} qty={qty:.6f} entry={signal.entry:.4f} "
            f"SL={signal.stop_loss:.4f} TP={signal.take_profit:.4f} lev={signal.leverage}x "
            f"regime={signal.regime} strength={signal.strength:.2f}"
        )
        return

    try:
        market_order = exchange.create_market_order(symbol, side, qty, params={"tdMode": "cross"})
        logger.info(f"Market order: {json.dumps(market_order, default=str)}")
    except Exception as e:
        logger.error(f"Market order failed: {e}")
        return

    # Best effort protection orders.
    for label, trigger_price in (("SL", signal.stop_loss), ("TP", signal.take_profit)):
        try:
            exchange.create_order(
                symbol=symbol,
                type="trigger",
                side=exit_side,
                amount=qty,
                price=None,
                params={
                    "triggerPrice": trigger_price,
                    "orderPrice": -1,
                    "reduceOnly": True,
                    "tdMode": "cross",
                },
            )
            logger.info(f"{label} placed at {trigger_price:.4f}")
        except Exception as e:
            logger.warning(f"{label} failed: {e}")


# ============================
# Main loop
# ============================


def process_symbol(exchange: ccxt.okx, state: BotState, symbol: str) -> None:
    """دورة قرار واحدة لعملة واحدة (تُستخدم في الوضعين)."""
    pos = get_open_position(exchange, symbol)
    if pos:
        logger.info(
            f"[{symbol}] Open position exists, skipping: side={pos.get('side')} "
            f"contracts={pos.get('contracts')}"
        )
        return

    df = fetch_ohlcv_df(exchange, symbol, TIMEFRAME, LOOKBACK)
    equity = get_equity_usdt(exchange)
    if equity <= 0 and PAPER_TRADING:
        equity = 10.0

    if not daily_drawdown_guard(state, equity):
        state.trading_enabled = False
        logger.warning("Daily drawdown limit reached. Trading paused.")

    if not state.trading_enabled:
        return

    signal = generate_signal(df)
    if not signal:
        logger.info(f"[{symbol}] No signal.")
        return

    if state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        state.trading_enabled = False
        logger.warning("Consecutive loss limit reached. Trading paused.")
        return

    qty = position_size(equity, signal.entry, signal.stop_loss, signal.leverage)

    logger.info(
        f"[{symbol}] Signal={signal.side.upper()} regime={signal.regime} "
        f"entry={signal.entry:.4f} sl={signal.stop_loss:.4f} tp={signal.take_profit:.4f} "
        f"lev={signal.leverage}x qty={qty:.6f} equity={equity:.2f}"
    )

    set_leverage(exchange, symbol, signal.leverage)
    submit_order(exchange, symbol, signal, qty)


def run() -> None:
    # ⛔ قيد المالك: لا BTC ولا ETH ولا SOL
    symbols = SYMBOLS if RUN_ONCE else [SYMBOL]
    symbols = [s for s in symbols
               if not any(b in s.upper() for b in BANNED_ASSETS)]
    if not symbols:
        logger.error("كل الرموز المطلوبة محظورة بقيد المالك (بدون BTC/ETH/SOL).")
        return

    exchange = build_exchange()
    state = BotState()

    logger.info("Loading markets...")
    exchange.load_markets()

    for s in symbols:
        if s not in exchange.markets:
            logger.warning(f"Symbol not found: {s}. Check OKX market naming.")

    mode = "RUN_ONCE (GitHub Actions)" if RUN_ONCE else "LOOP (server)"
    logger.info(
        f"Starting | mode={mode} symbols={symbols} timeframe={TIMEFRAME} "
        f"paper={PAPER_TRADING} demo={OKX_DEMO} baseLev={BASE_LEVERAGE}x"
    )

    if RUN_ONCE:
        # وضع GitHub Actions: مسح كل العملات مرة واحدة ثم الخروج
        for s in symbols:
            try:
                process_symbol(exchange, state, s)
            except Exception as e:
                logger.exception(f"[{s}] error: {e}")
        logger.info("Cycle complete — exiting (RUN_ONCE).")
        return

    # وضع الخادم الدائم (الأصلي)
    while True:
        try:
            process_symbol(exchange, state, symbols[0])
            time.sleep(POLL_SECONDS)
        except ccxt.NetworkError as e:
            logger.warning(f"Network error: {e}")
            time.sleep(POLL_SECONDS)
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error: {e}")
            time.sleep(POLL_SECONDS)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
