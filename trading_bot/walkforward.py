"""
اختبار المتانة (Walk-forward / تقسيم زمني).

بدلًا من قياس الأداء على فترة واحدة (قد تكون حظًا)، نقسّم التاريخ
إلى عدة شرائح زمنية متتابعة ونقيس الأداء في كل شريحة على حدة.

إذا ربحت الاستراتيجية في معظم الشرائح → فهي متينة.
إذا ربحت في شريحة واحدة فقط وخسرت في الباقي → فهي حظ، ليست متانة.
"""
import argparse

import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from strategy import entry_signal, compute_stops, position_size


def simulate(df, capital):
    """محاكاة مبسّطة على DataFrame مُجهّز بالمؤشرات. تعيد رأس المال النهائي وعدد الصفقات."""
    trades = 0
    wins = 0
    position = None
    for i in range(1, len(df)):
        row = df.iloc[i]
        if position is not None:
            exit_price = None
            if row["low"] <= position["stop_loss"]:
                exit_price = position["stop_loss"]
            elif row["high"] >= position["take_profit"]:
                exit_price = position["take_profit"]
            if exit_price is None and cfg.USE_TRAILING_STOP:
                new_stop = row["close"] - row["atr"] * cfg.TRAILING_ATR_MULTIPLIER
                if new_stop > position["stop_loss"]:
                    position["stop_loss"] = new_stop
            if exit_price is not None:
                gross = (exit_price - position["entry_price"]) * position["qty"]
                fees = (position["entry_price"] + exit_price) * position["qty"] * cfg.TAKER_FEE
                pnl = gross - fees
                capital += pnl
                trades += 1
                if pnl > 0:
                    wins += 1
                position = None
        if position is None and entry_signal(df, i, cfg):
            entry_price = row["close"]
            stop_loss, take_profit = compute_stops(entry_price, row["atr"], cfg)
            qty = position_size(capital, entry_price, stop_loss, cfg)
            required_margin = entry_price * qty / cfg.MAX_LEVERAGE
            if qty > 0 and required_margin <= capital:
                position = {
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "qty": qty,
                }
    return capital, trades, wins


def main():
    parser = argparse.ArgumentParser(description="اختبار المتانة walk-forward")
    parser.add_argument("--candles", type=int, default=4000)
    parser.add_argument("--folds", type=int, default=4, help="عدد الشرائح الزمنية")
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    args = parser.parse_args()

    print(f"🔬 اختبار المتانة: {args.folds} شرائح زمنية، {len(args.symbols)} أزواج\n")

    fold_results = {f: [] for f in range(args.folds)}

    for symbol in args.symbols:
        try:
            df = fetch_history(symbol, total=args.candles)
            df = add_indicators(df, cfg)
        except Exception as e:
            print(f"✗ {symbol}: {e}")
            continue

        # نتجاهل أول 200 شمعة (تسخين المؤشرات) ثم نقسّم الباقي
        df = df.iloc[cfg.EMA_TREND_SLOW:].reset_index(drop=True)
        fold_size = len(df) // args.folds
        if fold_size < 50:
            print(f"✗ {symbol}: بيانات غير كافية للتقسيم")
            continue

        for f in range(args.folds):
            chunk = df.iloc[f * fold_size:(f + 1) * fold_size].reset_index(drop=True)
            final_cap, trades, wins = simulate(chunk, cfg.INITIAL_CAPITAL)
            ret = (final_cap - cfg.INITIAL_CAPITAL) / cfg.INITIAL_CAPITAL * 100
            fold_results[f].append(ret)

    # تقرير لكل شريحة
    print("=" * 56)
    print(f"{'الشريحة':<12}{'متوسط العائد':<16}{'أزواج رابحة':<16}")
    print("-" * 56)
    overall = []
    for f in range(args.folds):
        rets = fold_results[f]
        if not rets:
            continue
        avg = np.mean(rets)
        winners = sum(1 for r in rets if r > 0)
        overall.extend(rets)
        flag = "✅" if avg > 0 else "❌"
        print(f"الشريحة {f+1:<6}{avg:+.2f}%{'':<10}{winners}/{len(rets)}  {flag}")
    print("=" * 56)

    if overall:
        positive_folds = sum(1 for f in range(args.folds)
                             if fold_results[f] and np.mean(fold_results[f]) > 0)
        active_folds = sum(1 for f in range(args.folds) if fold_results[f])
        print(f"\nمتوسط العائد الكلي:  {np.mean(overall):+.2f}%")
        print(f"شرائح رابحة:         {positive_folds}/{active_folds}")
        print(f"تباين العوائد (انحراف معياري): {np.std(overall):.2f}%")

        print("\n📌 الحكم:")
        if positive_folds == active_folds:
            print("   متينة نسبيًا — رابحة في كل الشرائح الزمنية. ✅")
        elif positive_folds >= active_folds * 0.6:
            print("   متوسطة المتانة — رابحة في غالبية الفترات لكنها غير ثابتة. ⚠️")
        else:
            print("   ضعيفة المتانة — أداؤها يعتمد على فترة معيّنة (حظ). ❌")


if __name__ == "__main__":
    main()
