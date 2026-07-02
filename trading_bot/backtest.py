"""
محرّك الاختبار التاريخي (Backtest).

يحاكي تنفيذ الاستراتيجية على بيانات الماضي مع نموذج واقعي:
  - الدخول عند إغلاق شمعة الإشارة.
  - الخروج عند ضرب وقف الخسارة أو جني الأرباح (يُفحص على نطاق الشمعة التالية).
  - خصم الرسوم في كل من الدخول والخروج.
  - وقف متحرك اختياري.

يطبع تقريرًا بالأداء: العائد، نسبة النجاح، أكبر تراجع، عامل الربح.
"""
import argparse

import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from strategy import entry_signal, compute_stops, position_size


def run_symbol(symbol, total_candles, capital, verbose=False):
    """تشغيل الاختبار على زوج واحد. يعيد قائمة الصفقات ورأس المال النهائي."""
    df = fetch_history(symbol, total=total_candles)
    df = add_indicators(df, cfg)

    trades = []
    position = None  # الصفقة المفتوحة الحالية

    for i in range(1, len(df)):
        row = df.iloc[i]

        # ---- إدارة صفقة مفتوحة ----
        if position is not None:
            exit_price = None
            reason = None
            d = position["direction"]

            # فحص ضرب المستويات داخل نطاق الشمعة الحالية (حسب الاتجاه)
            if d == 1:
                if row["low"] <= position["stop_loss"]:
                    exit_price, reason = position["stop_loss"], "stop_loss"
                elif row["high"] >= position["take_profit"]:
                    exit_price, reason = position["take_profit"], "take_profit"
            else:  # صفقة بيع
                if row["high"] >= position["stop_loss"]:
                    exit_price, reason = position["stop_loss"], "stop_loss"
                elif row["low"] <= position["take_profit"]:
                    exit_price, reason = position["take_profit"], "take_profit"

            # تحديث الوقف المتحرك (يحرّك الوقف في اتجاه الربح فقط)
            if exit_price is None and cfg.USE_TRAILING_STOP:
                offset = row["atr"] * cfg.TRAILING_ATR_MULTIPLIER
                if d == 1:
                    new_stop = row["close"] - offset
                    if new_stop > position["stop_loss"]:
                        position["stop_loss"] = new_stop
                else:
                    new_stop = row["close"] + offset
                    if new_stop < position["stop_loss"]:
                        position["stop_loss"] = new_stop

            if exit_price is not None:
                gross = (exit_price - position["entry_price"]) * position["qty"] * d
                fees = (position["entry_price"] + exit_price) * position["qty"] * cfg.TAKER_FEE
                pnl = gross - fees
                capital += pnl
                trades.append({
                    "symbol": symbol,
                    "direction": "LONG" if d == 1 else "SHORT",
                    "entry_time": position["entry_time"],
                    "exit_time": row["ts"],
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "qty": position["qty"],
                    "pnl": pnl,
                    "return_pct": pnl / position["cost"] * 100,
                    "reason": reason,
                    "capital_after": capital,
                })
                if verbose:
                    tag = "LONG" if d == 1 else "SHORT"
                    print(f"  [{symbol}/{tag}] خروج {reason} | ربح/خسارة: {pnl:+.2f} | رأس المال: {capital:.2f}")
                position = None

        # ---- البحث عن دخول جديد ----
        if position is None:
            direction = entry_signal(df, i, cfg)
            if direction != 0:
                entry_price = row["close"]
                stop_loss, take_profit = compute_stops(entry_price, row["atr"], direction, cfg)
                qty = position_size(capital, entry_price, stop_loss, cfg)
                cost = entry_price * qty
                # في العقود الآجلة: الهامش المطلوب = القيمة الاسمية / الرافعة
                required_margin = cost / cfg.MAX_LEVERAGE
                if qty > 0 and required_margin <= capital:
                    position = {
                        "direction": direction,
                        "entry_time": row["ts"],
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "qty": qty,
                        "cost": cost,
                    }
                    if verbose:
                        tag = "LONG" if direction == 1 else "SHORT"
                        print(f"  [{symbol}/{tag}] دخول @ {entry_price:.4f} | SL {stop_loss:.4f} | TP {take_profit:.4f}")

    return trades, capital


def performance_report(trades, initial_capital, final_capital):
    """حساب وطباعة مقاييس الأداء."""
    if not trades:
        print("\n⚠️  لا توجد صفقات في هذه الفترة.")
        return

    df = pd.DataFrame(trades)
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] <= 0]

    total_return = (final_capital - initial_capital) / initial_capital * 100
    win_rate = len(wins) / len(df) * 100
    avg_win = wins["pnl"].mean() if len(wins) else 0
    avg_loss = losses["pnl"].mean() if len(losses) else 0
    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # أكبر تراجع (Max Drawdown) من منحنى رأس المال
    equity = pd.concat([
        pd.Series([initial_capital]),
        df["capital_after"].reset_index(drop=True),
    ], ignore_index=True)
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max * 100
    max_dd = drawdown.min()

    print("\n" + "=" * 50)
    print("           📊  تقرير الأداء")
    print("=" * 50)
    print(f"  رأس المال الابتدائي:   {initial_capital:,.2f} $")
    print(f"  رأس المال النهائي:     {final_capital:,.2f} $")
    print(f"  العائد الإجمالي:       {total_return:+.2f} %")
    print("-" * 50)
    print(f"  عدد الصفقات:           {len(df)}")
    print(f"  الصفقات الرابحة:       {len(wins)}")
    print(f"  الصفقات الخاسرة:       {len(losses)}")
    print(f"  نسبة النجاح:           {win_rate:.1f} %")
    print("-" * 50)
    print(f"  متوسط الربح:           {avg_win:+.2f} $")
    print(f"  متوسط الخسارة:         {avg_loss:+.2f} $")
    print(f"  عامل الربح:            {profit_factor:.2f}")
    print(f"  أكبر تراجع:            {max_dd:.2f} %")
    print("=" * 50)

    # توزيع أسباب الخروج
    print("\n  أسباب الخروج:")
    for reason, count in df["reason"].value_counts().items():
        print(f"    {reason}: {count}")


def main():
    parser = argparse.ArgumentParser(description="محرّك الاختبار التاريخي")
    parser.add_argument("--candles", type=int, default=1500,
                        help="عدد الشموع التاريخية لكل زوج")
    parser.add_argument("--verbose", action="store_true",
                        help="طباعة تفاصيل كل صفقة")
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS,
                        help="الأزواج المراد اختبارها")
    args = parser.parse_args()

    all_trades = []
    print(f"🔍 بدء الاختبار التاريخي على {len(args.symbols)} زوج، إطار {cfg.TIMEFRAME}")
    print(f"   رأس المال الابتدائي: {cfg.INITIAL_CAPITAL} $\n")

    # نوزّع رأس المال لكل زوج بشكل مستقل لقياس أداء الاستراتيجية لكل زوج
    per_symbol_capital = cfg.INITIAL_CAPITAL
    for symbol in args.symbols:
        print(f"▶ {symbol} ...")
        try:
            trades, final_cap = run_symbol(symbol, args.candles,
                                           per_symbol_capital, args.verbose)
        except Exception as e:
            print(f"  ✗ خطأ في {symbol}: {e}")
            continue
        ret = (final_cap - per_symbol_capital) / per_symbol_capital * 100
        print(f"  ✓ {len(trades)} صفقة | العائد: {ret:+.2f}%")
        all_trades.extend(trades)

    # تقرير مجمّع: نطبّق الصفقات بالترتيب الزمني على رأس مال واحد
    if all_trades:
        all_trades.sort(key=lambda t: t["entry_time"])
        capital = cfg.INITIAL_CAPITAL
        for t in all_trades:
            capital += t["pnl"]
            t["capital_after"] = capital
        performance_report(all_trades, cfg.INITIAL_CAPITAL, capital)


if __name__ == "__main__":
    main()
