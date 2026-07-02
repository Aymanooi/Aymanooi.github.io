"""
محرّك التحسين الذكي مع التحقّق خارج العيّنة (Out-of-Sample Validation).

هذا هو "العقل" الحقيقي للنظام. بدلًا من تخمين المعاملات يدويًا (ما يؤدي
إلى خداع النفس / Overfitting)، يقوم تلقائيًا بـ:

  1. تقسيم البيانات:  70% تدريب (In-Sample) + 30% اختبار (Out-of-Sample).
  2. البحث في شبكة واسعة من تركيبات المعاملات على بيانات التدريب فقط.
  3. اختيار أفضل تركيبة حسب معيار الجودة (عامل الربح المعدّل).
  4. اختبار تلك التركيبة على بيانات لم ترها قط (Out-of-Sample).

الحكم الصادق:
  • إن نجحت في الاثنين  → ميزة حقيقية محتملة.
  • إن نجحت في التدريب وفشلت في الاختبار → وهم (أثبتنا الـ Overfitting بأنفسنا).

هذا ما تفعله صناديق التحوّط فعلًا. هو يحمينا من الكذب على أنفسنا.
"""
import argparse
import itertools
import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from strategy import entry_signal, compute_stops, position_size


# ===== شبكة البحث (المعاملات التي نجرّبها) =====
PARAM_GRID = {
    "EMA_FAST": [7, 9, 12],
    "EMA_SLOW": [21, 26, 34],
    "ADX_MIN": [20, 25, 30],
    "ATR_STOP_MULTIPLIER": [1.0, 1.5, 2.0],
    "RISK_REWARD_RATIO": [1.5, 2.0, 3.0],
}


def make_params(overrides):
    """إنشاء كائن إعدادات مؤقت يدمج config مع التعديلات."""
    base = {k: getattr(cfg, k) for k in dir(cfg) if k.isupper()}
    base.update(overrides)
    return SimpleNamespace(**base)


def simulate(df, params):
    """محاكاة على DataFrame مُجهّز مسبقًا بالمؤشرات. تعيد قاموس مقاييس."""
    capital = params.INITIAL_CAPITAL
    position = None
    pnls = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        if position is not None:
            exit_price = None
            d = position["direction"]
            if d == 1:
                if row["low"] <= position["stop_loss"]:
                    exit_price = position["stop_loss"]
                elif row["high"] >= position["take_profit"]:
                    exit_price = position["take_profit"]
            else:
                if row["high"] >= position["stop_loss"]:
                    exit_price = position["stop_loss"]
                elif row["low"] <= position["take_profit"]:
                    exit_price = position["take_profit"]
            if exit_price is None and params.USE_TRAILING_STOP:
                offset = row["atr"] * params.TRAILING_ATR_MULTIPLIER
                if d == 1:
                    position["stop_loss"] = max(position["stop_loss"], row["close"] - offset)
                else:
                    position["stop_loss"] = min(position["stop_loss"], row["close"] + offset)
            if exit_price is not None:
                gross = (exit_price - position["entry_price"]) * position["qty"] * d
                fees = (position["entry_price"] + exit_price) * position["qty"] * params.TAKER_FEE
                pnl = gross - fees
                capital += pnl
                pnls.append(pnl)
                position = None
        if position is None:
            direction = entry_signal(df, i, params)
            if direction != 0:
                entry_price = row["close"]
                stop_loss, take_profit = compute_stops(entry_price, row["atr"], direction, params)
                qty = position_size(capital, entry_price, stop_loss, params)
                if qty > 0 and entry_price * qty / params.MAX_LEVERAGE <= capital:
                    position = {
                        "direction": direction, "entry_price": entry_price,
                        "stop_loss": stop_loss, "take_profit": take_profit, "qty": qty,
                    }

    return _metrics(pnls, params.INITIAL_CAPITAL, capital)


def _metrics(pnls, initial, final):
    """حساب مقاييس الأداء من قائمة الأرباح/الخسائر."""
    n = len(pnls)
    if n == 0:
        return {"trades": 0, "return_pct": 0.0, "win_rate": 0.0,
                "profit_factor": 0.0, "score": -999}
    pnls = np.array(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
    ret = (final - initial) / initial * 100
    win_rate = len(wins) / n * 100
    # معيار الجودة: عامل الربح، مع عقوبة لقلّة الصفقات (نتجنّب نتائج عيّنة صغيرة)
    sample_penalty = min(1.0, n / 15)
    score = (pf - 1.0) * sample_penalty
    return {"trades": n, "return_pct": ret, "win_rate": win_rate,
            "profit_factor": pf, "score": score}


def prepare(df, params):
    """إضافة المؤشرات بمعاملات محددة (تتغيّر مع كل تركيبة)."""
    return add_indicators(df, params)


def optimize_symbol(symbol, total_candles):
    """تشغيل التحسين الكامل على زوج واحد."""
    raw = fetch_history(symbol, total=total_candles)
    split = int(len(raw) * 0.7)
    is_raw = raw.iloc[:split].reset_index(drop=True)       # تدريب
    oos_raw = raw.iloc[split:].reset_index(drop=True)      # اختبار خارج العيّنة

    keys = list(PARAM_GRID.keys())
    combos = list(itertools.product(*PARAM_GRID.values()))

    best = None
    for values in combos:
        overrides = dict(zip(keys, values))
        # نتخطى التركيبات غير المنطقية
        if overrides["EMA_FAST"] >= overrides["EMA_SLOW"]:
            continue
        params = make_params(overrides)
        is_df = prepare(is_raw, params)
        m = simulate(is_df, params)
        if m["trades"] < 8:   # نحتاج عيّنة كافية
            continue
        if best is None or m["score"] > best["is"]["score"]:
            best = {"overrides": overrides, "is": m}

    if best is None:
        return None

    # اختبار أفضل تركيبة على البيانات غير المرئية
    params = make_params(best["overrides"])
    oos_df = prepare(oos_raw, params)
    best["oos"] = simulate(oos_df, params)
    best["symbol"] = symbol
    return best


def main():
    parser = argparse.ArgumentParser(description="محرّك التحسين مع تحقّق خارج العيّنة")
    parser.add_argument("--candles", type=int, default=4000)
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    args = parser.parse_args()

    grid_size = 1
    for v in PARAM_GRID.values():
        grid_size *= len(v)
    print(f"🧠 محرّك التحسين الذكي")
    print(f"   {len(args.symbols)} أزواج × {grid_size} تركيبة لكل زوج")
    print(f"   تقسيم: 70% تدريب / 30% اختبار خارج العيّنة\n")

    results = []
    for symbol in args.symbols:
        print(f"▶ تحسين {symbol} ...")
        try:
            best = optimize_symbol(symbol, args.candles)
        except Exception as e:
            print(f"  ✗ خطأ: {e}")
            continue
        if best is None:
            print("  ⚠️ لا توجد تركيبة صالحة")
            continue
        results.append(best)
        print(f"  أفضل تركيبة: {best['overrides']}")
        print(f"    التدريب (In-Sample):       عائد {best['is']['return_pct']:+.1f}% | "
              f"PF {best['is']['profit_factor']:.2f} | {best['is']['trades']} صفقة")
        print(f"    الاختبار (Out-of-Sample):  عائد {best['oos']['return_pct']:+.1f}% | "
              f"PF {best['oos']['profit_factor']:.2f} | {best['oos']['trades']} صفقة")
        print()

    # الحكم النهائي
    if results:
        print("=" * 60)
        print("                  📊  الحكم النهائي")
        print("=" * 60)
        is_avg = np.mean([r["is"]["return_pct"] for r in results])
        oos_avg = np.mean([r["oos"]["return_pct"] for r in results])
        oos_winners = sum(1 for r in results if r["oos"]["return_pct"] > 0)
        oos_pf_avg = np.mean([r["oos"]["profit_factor"] for r in results])
        print(f"  متوسط عائد التدريب:           {is_avg:+.2f}%")
        print(f"  متوسط عائد الاختبار الحقيقي:  {oos_avg:+.2f}%")
        print(f"  عامل الربح (خارج العيّنة):     {oos_pf_avg:.2f}")
        print(f"  أزواج رابحة خارج العيّنة:      {oos_winners}/{len(results)}")
        print("=" * 60)
        print("\n📌 التفسير:")
        if oos_avg > 0 and oos_winners >= len(results) * 0.6 and oos_pf_avg > 1.1:
            print("   إشارة واعدة — صمدت خارج العيّنة. تستحق اختبار محاكاة حي.")
        elif is_avg > 0 and oos_avg <= 0:
            print("   Overfitting مؤكّد — ربحت في التدريب وفشلت في الواقع.")
            print("   هذا دليل علمي أن التركيبات لا تملك ميزة حقيقية.")
        else:
            print("   لا توجد ميزة واضحة حتى مع البحث الآلي الواسع.")


if __name__ == "__main__":
    main()
