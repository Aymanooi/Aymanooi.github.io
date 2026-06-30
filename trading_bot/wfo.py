"""
[8] Walk-Forward Optimization — التحسين المتدحرج للأمام.

أرقى من تقسيم تدريب/اختبار واحد. نقسّم التاريخ إلى نوافذ متتالية:
يُحسّن المعاملات على نافذة تدريب، ثم يُختبر على النافذة التالية مباشرة،
ثم تتدحرج النافذتان للأمام. النتيجة النهائية = تجميع كل فترات الاختبار
(out-of-sample) — أقرب ما يكون لمحاكاة التداول الحقيقي عبر الزمن.
"""
import argparse
import itertools

import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from optimizer import make_params, simulate, PARAM_GRID


def walk_forward(symbol, total_candles, n_windows=4, train_ratio=0.7):
    """تشغيل التحسين المتدحرج على زوج. يعيد قائمة عوائد الاختبار لكل نافذة."""
    raw = fetch_history(symbol, total=total_candles)
    win_size = len(raw) // n_windows
    keys = list(PARAM_GRID.keys())
    combos = [c for c in itertools.product(*PARAM_GRID.values())]

    oos_returns = []
    for w in range(n_windows - 1):
        # نافذة التدريب الحالية + نافذة الاختبار التالية
        seg = raw.iloc[w * win_size:(w + 2) * win_size].reset_index(drop=True)
        split = int(len(seg) * train_ratio)
        is_raw = seg.iloc[:split].reset_index(drop=True)
        oos_raw = seg.iloc[split:].reset_index(drop=True)

        best = None
        for values in combos:
            ov = dict(zip(keys, values))
            if ov["EMA_FAST"] >= ov["EMA_SLOW"]:
                continue
            params = make_params(ov)
            m = simulate(add_indicators(is_raw, params), params)
            if m["trades"] < 5:
                continue
            if best is None or m["score"] > best[1]["score"]:
                best = (ov, m)
        if best is None:
            continue
        # اختبار أفضل تركيبة على النافذة التالية غير المرئية
        params = make_params(best[0])
        oos_m = simulate(add_indicators(oos_raw, params), params)
        oos_returns.append(oos_m["return_pct"])

    return oos_returns


def main():
    parser = argparse.ArgumentParser(description="التحسين المتدحرج للأمام")
    parser.add_argument("--candles", type=int, default=4000)
    parser.add_argument("--windows", type=int, default=4)
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    args = parser.parse_args()

    print("🚶 Walk-Forward Optimization")
    print(f"   {args.windows} نوافذ متدحرجة | تحسين ثم اختبار خارج العيّنة\n")

    all_oos = []
    for symbol in args.symbols:
        rets = walk_forward(symbol, args.candles, args.windows)
        if not rets:
            print(f"  {symbol}: لا نتائج كافية")
            continue
        avg = np.mean(rets)
        all_oos.extend(rets)
        print(f"  {symbol}: نوافذ الاختبار {[f'{r:+.1f}%' for r in rets]} | متوسط {avg:+.2f}%")

    if all_oos:
        print(f"\n  المتوسط الكلي خارج العيّنة: {np.mean(all_oos):+.2f}%")
        print(f"  نوافذ رابحة: {sum(1 for r in all_oos if r > 0)}/{len(all_oos)}")


if __name__ == "__main__":
    main()
