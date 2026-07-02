"""
محرّك المحاكاة (Paper Trading) — يشغّل البوت بأموال وهمية على بيانات السوق الحقيقية.

الهدف المطلوب: تحويل 1$ إلى 10$ برأس مال كامل ورافعة 10x.

⚠️ هذا وضع محاكاة (بلا أموال حقيقية). يوضّح بالضبط ماذا كان سيحدث لو
شغّلت هذه الإعدادات بمالك. التصفية (Liquidation) محسوبة كما في الواقع:
أي حركة عكسية تتجاوز (1 / الرافعة) تمحو الحساب بالكامل.
"""
import argparse
import numpy as np

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from strategy import entry_signal, compute_stops

START = 1.0
TARGET = 10.0
LEVERAGE = 10.0
FEE = cfg.TAKER_FEE


def run(symbol, candles, verbose=True):
    df = add_indicators(fetch_history(symbol, total=candles), cfg)
    capital = START
    position = None
    trade_log = []

    for i in range(1, len(df)):
        row = df.iloc[i]

        if position is not None:
            d = position["dir"]
            entry = position["entry"]
            qty = position["qty"]
            exit_price = reason = None

            # حدّ التصفية: حركة عكسية بمقدار (1/الرافعة) تمحو الهامش
            liq_move = 1.0 / LEVERAGE
            if d == 1:
                liq_price = entry * (1 - liq_move)
                if row["low"] <= liq_price:
                    exit_price, reason = liq_price, "💀 تصفية"
                elif row["low"] <= position["sl"]:
                    exit_price, reason = position["sl"], "وقف خسارة"
                elif row["high"] >= position["tp"]:
                    exit_price, reason = position["tp"], "جني ربح"
            else:
                liq_price = entry * (1 + liq_move)
                if row["high"] >= liq_price:
                    exit_price, reason = liq_price, "💀 تصفية"
                elif row["high"] >= position["sl"]:
                    exit_price, reason = position["sl"], "وقف خسارة"
                elif row["low"] <= position["tp"]:
                    exit_price, reason = position["tp"], "جني ربح"

            if exit_price is not None:
                pnl = (exit_price - entry) * qty * d
                pnl -= (entry + exit_price) * qty * FEE
                capital += pnl
                capital = max(0.0, capital)
                trade_log.append((reason, capital))
                if verbose:
                    print(f"  {reason:12s} | رأس المال: {capital:6.2f}$")
                position = None
                if capital >= TARGET:
                    return capital, trade_log, "🎯 وصلنا للهدف!"
                if capital < 0.10:
                    return capital, trade_log, "💥 إفلاس"

        if position is None:
            d = entry_signal(df, i, cfg)
            if d != 0 and not np.isnan(row["atr"]) and row["atr"] > 0:
                entry = row["close"]
                sl, tp = compute_stops(entry, row["atr"], d, cfg)
                qty = capital * LEVERAGE / entry   # رأس مال كامل × الرافعة
                position = {"dir": d, "entry": entry, "sl": sl, "tp": tp, "qty": qty}

    return capital, trade_log, "انتهت البيانات"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candles", type=int, default=2000)
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    args = parser.parse_args()

    print("=" * 56)
    print("   📟 محاكاة حيّة: 1$ → 10$ | رأس مال كامل | رافعة 10x")
    print("=" * 56)
    print("   ⚠️ أموال وهمية — لحمايتك\n")

    outcomes = []
    for symbol in args.symbols:
        print(f"▶ {symbol}")
        cap, log, status = run(symbol, args.candles)
        print(f"  النتيجة: {status} | رأس المال النهائي: {cap:.2f}$ ({len(log)} صفقة)\n")
        outcomes.append((symbol, cap, status))

    print("=" * 56)
    wins = sum(1 for _, c, _ in outcomes if c >= TARGET)
    busts = sum(1 for _, c, _ in outcomes if c < 0.10)
    print(f"   وصل للهدف 10$: {wins}/{len(outcomes)} | أفلس: {busts}/{len(outcomes)}")
    print("=" * 56)


if __name__ == "__main__":
    main()
