import os
import json
import logging
from datetime import datetime

import pandas as pd
import ta
import anthropic
from pybit.unified_trading import HTTP

from config import (
    TRADING_PAIRS, KLINE_INTERVAL, KLINE_LIMIT,
    MAX_POSITION_PCT, MIN_CONFIDENCE, MIN_TRADE_USDT, ACCOUNT_TYPE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

bybit = HTTP(
    testnet=os.getenv("BYBIT_TESTNET", "false").lower() == "true",
    api_key=os.getenv("BYBIT_API_KEY"),
    api_secret=os.getenv("BYBIT_API_SECRET"),
)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_market_data(symbol: str) -> pd.DataFrame:
    resp = bybit.get_kline(
        category="linear",
        symbol=symbol,
        interval=KLINE_INTERVAL,
        limit=KLINE_LIMIT,
    )
    rows = resp["result"]["list"]
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df = df.iloc[::-1].reset_index(drop=True)
    return df


def calculate_indicators(df: pd.DataFrame) -> dict:
    rsi = ta.momentum.RSIIndicator(df["close"], window=14).rsi().iloc[-1]
    macd = ta.trend.MACD(df["close"])
    macd_diff = macd.macd_diff().iloc[-1]
    bb = ta.volatility.BollingerBands(df["close"])
    bb_pct = bb.bollinger_pband().iloc[-1]

    return {
        "current_price": df["close"].iloc[-1],
        "rsi": round(rsi, 2),
        "macd_diff": round(macd_diff, 4),
        "bb_position_pct": round(bb_pct * 100, 2),
        "volume_24h": round(df["volume"].tail(24).sum(), 2),
        "price_change_24h_pct": round(
            (df["close"].iloc[-1] - df["close"].iloc[-24]) / df["close"].iloc[-24] * 100, 2
        ),
    }


def get_account_info() -> dict:
    resp = bybit.get_wallet_balance(accountType=ACCOUNT_TYPE, coin="USDT")
    coins = resp["result"]["list"][0]["coin"]
    usdt = next((c for c in coins if c["coin"] == "USDT"), {})
    return {
        "available_balance": float(usdt.get("availableToWithdraw", 0)),
        "total_equity": float(usdt.get("equity", 0)),
    }


def get_open_position(symbol: str) -> dict:
    resp = bybit.get_positions(category="linear", symbol=symbol)
    positions = resp["result"]["list"]
    if not positions:
        return {"side": "None", "size": 0, "unrealized_pnl": 0}
    p = positions[0]
    return {
        "side": p.get("side", "None"),
        "size": float(p.get("size", 0)),
        "unrealized_pnl": float(p.get("unrealisedPnl", 0)),
    }


def analyze_with_claude(symbol: str, indicators: dict, position: dict, balance: float) -> dict:
    prompt = f"""أنت محلل تداول خبير في العملات الرقمية. قدم قرار تداول واحد بناءً على البيانات التالية.

الزوج: {symbol}
السعر الحالي: {indicators['current_price']} USDT
التغير 24h: {indicators['price_change_24h_pct']}%
RSI (14): {indicators['rsi']}
MACD Histogram: {indicators['macd_diff']}
موقع Bollinger Bands: {indicators['bb_position_pct']}% (0=أسفل النطاق، 100=أعلى النطاق)
حجم التداول 24h: {indicators['volume_24h']}

المركز الحالي: {position['side']} | الحجم: {position['size']} | P&L: {position['unrealized_pnl']} USDT
الرصيد المتاح: {balance} USDT

قواعد:
- إذا RSI > 70 وBollinger > 80: احتمال البيع مرتفع
- إذا RSI < 30 وBollinger < 20: احتمال الشراء مرتفع
- لا تتجاوز 15% من الرصيد في صفقة واحدة
- إذا كان هناك مركز مفتوح بالفعل في نفس الاتجاه، اختر HOLD

أجب بـ JSON فقط بدون أي نص إضافي:
{{
  "action": "BUY|SELL|HOLD",
  "percentage": 5,
  "confidence": 75,
  "reason": "سبب القرار باختصار"
}}"""

    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)


def execute_trade(symbol: str, action: str, usdt_amount: float, current_price: float) -> None:
    if usdt_amount < MIN_TRADE_USDT:
        log.info(f"[{symbol}] حجم الصفقة {usdt_amount:.2f} USDT أصغر من الحد الأدنى {MIN_TRADE_USDT} USDT - تم التجاهل")
        return

    qty = round(usdt_amount / current_price, 4)
    side = "Buy" if action == "BUY" else "Sell"

    if DRY_RUN:
        log.info(f"[DRY_RUN] [{symbol}] {side} qty={qty} (~{usdt_amount:.2f} USDT @ {current_price})")
        return

    resp = bybit.place_order(
        category="linear",
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=str(qty),
        timeInForce="IOC",
    )
    log.info(f"[{symbol}] صفقة {side}: qty={qty} | orderId={resp['result'].get('orderId')}")


def process_symbol(symbol: str, account: dict) -> None:
    log.info(f"--- معالجة {symbol} ---")
    try:
        df = get_market_data(symbol)
        indicators = calculate_indicators(df)
        position = get_open_position(symbol)
        balance = account["available_balance"]

        log.info(f"[{symbol}] السعر={indicators['current_price']} RSI={indicators['rsi']} BB={indicators['bb_position_pct']}%")

        decision = analyze_with_claude(symbol, indicators, position, balance)
        log.info(f"[{symbol}] قرار Claude: {decision['action']} | confidence={decision['confidence']}% | {decision['reason']}")

        if decision["action"] == "HOLD":
            log.info(f"[{symbol}] HOLD - لا يوجد إجراء")
            return

        if decision["confidence"] < MIN_CONFIDENCE:
            log.info(f"[{symbol}] confidence={decision['confidence']}% < {MIN_CONFIDENCE}% - تم التجاهل")
            return

        pct = min(decision["percentage"] / 100, MAX_POSITION_PCT)
        usdt_amount = balance * pct

        execute_trade(symbol, decision["action"], usdt_amount, indicators["current_price"])

    except Exception as e:
        log.error(f"[{symbol}] خطأ: {e}")


def run_bot() -> None:
    log.info(f"=== بدء الروبوت {'[DRY_RUN]' if DRY_RUN else '[LIVE]'} - {datetime.utcnow().isoformat()} ===")

    try:
        account = get_account_info()
        log.info(f"الرصيد المتاح: {account['available_balance']:.2f} USDT | الإجمالي: {account['total_equity']:.2f} USDT")
    except Exception as e:
        log.error(f"فشل في جلب معلومات الحساب: {e}")
        return

    for symbol in TRADING_PAIRS:
        process_symbol(symbol, account)

    log.info("=== انتهى الروبوت ===")


if __name__ == "__main__":
    run_bot()
