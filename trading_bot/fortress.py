"""
بوت القلعة — Momentum Confluence + فلتر Regime + كل أنظمة الحماية.

الإشارة:   Momentum Confluence (أفضل أداء في المختبر).
الفلاتر والحمايات المفعّلة كلها معًا:
  • Regime Filter        : شراء فقط في TREND_UP، بيع فقط في TREND_DOWN
                           (يشمل Anti-Chop: لا تداول في RANGE/HIGH_VOL)
  • Volatility Filter    : تداول فقط في نطاق تقلّب صحّي (20-90 مئوي، سببي)
  • Dynamic Risk Engine  : خفض المخاطرة للنصف بعد كل خسارتين متتاليتين
  • Drawdown Governor    : تراجع >15% من الذروة → نصف المخاطرة
  • Kill Switch          : تراجع >30% من الذروة → إيقاف كامل
  • Trade Cooldown       : انتظار 5 شموع بعد كل صفقة خاسرة

التقييم: اختبار الشرائح الزمنية مباشرةً (4 شرائح × 5 أزواج) —
الاختبار الذي أسقط كل مَن سبق.
"""
import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from strategy_lab import prepare, sig_momentum
from regime import detect_regime, TREND_UP, TREND_DOWN

FEE = cfg.TAKER_FEE


def simulate_fortress(df):
    """محاكاة بكل الحمايات. تعيد (العائد%, صفقات, نسبة نجاح, صفقات مرفوضة)."""
    capital = 1000.0
    peak = capital
    pos = None
    trades = wins = blocked = 0
    loss_streak = 0
    cooldown = 0
    killed = False

    # نطاق التقلّب الصحّي (سببي — expanding)
    atr_pct = df["atr"] / df["close"]
    lo_band = atr_pct.expanding(min_periods=50).quantile(0.20)
    hi_band = atr_pct.expanding(min_periods=50).quantile(0.90)

    for i in range(1, len(df)):
        r = df.iloc[i]

        # ---- إدارة الصفقة المفتوحة ----
        if pos is not None:
            d = pos["d"]
            hit = None
            if d == 1:
                if r["low"] <= pos["sl"]:
                    hit = pos["sl"]
                elif r["high"] >= pos["tp"]:
                    hit = pos["tp"]
            else:
                if r["high"] >= pos["sl"]:
                    hit = pos["sl"]
                elif r["low"] <= pos["tp"]:
                    hit = pos["tp"]
            if hit is not None:
                pnl = (hit - pos["e"]) * pos["q"] * d - (pos["e"] + hit) * pos["q"] * FEE
                capital += pnl
                trades += 1
                if pnl > 0:
                    wins += 1
                    loss_streak = 0
                else:
                    loss_streak += 1
                    cooldown = 5          # فترة تهدئة بعد الخسارة
                peak = max(peak, capital)
                pos = None

        if killed or pos is not None:
            continue

        # ---- Kill Switch ----
        if capital < peak * 0.70:
            killed = True
            continue

        # ---- Cooldown ----
        if cooldown > 0:
            cooldown -= 1
            continue

        # ---- إشارة الزخم ----
        d = sig_momentum(df, i)
        if d == 0:
            continue

        # ---- Regime Filter (مع Anti-Chop) ----
        reg = r["regime"]
        if (d == 1 and reg != TREND_UP) or (d == -1 and reg != TREND_DOWN):
            blocked += 1
            continue

        # ---- Volatility Filter ----
        ap = atr_pct.iloc[i]
        if pd.isna(lo_band.iloc[i]) or not (lo_band.iloc[i] <= ap <= hi_band.iloc[i]):
            blocked += 1
            continue

        # ---- Dynamic Risk + Drawdown Governor ----
        risk_frac = 0.02
        if loss_streak >= 2:
            risk_frac *= 0.5 ** (loss_streak // 2)
        if capital < peak * 0.85:
            risk_frac *= 0.5
        risk_frac = max(risk_frac, 0.005)

        # ---- فتح الصفقة ----
        if pd.isna(r["atr"]) or r["atr"] <= 0:
            continue
        e = r["close"]
        risk = r["atr"] * 1.5
        sl = e - risk * d
        tp = e + risk * 2 * d
        q = capital * risk_frac / risk
        if e * q / 10 <= capital:
            pos = {"d": d, "e": e, "sl": sl, "tp": tp, "q": q}

    ret = (capital - 1000) / 10
    wr = wins / trades * 100 if trades else 0
    return ret, trades, wr, blocked, killed


if __name__ == "__main__":
    print("=" * 64)
    print("  🏰 بوت القلعة: Momentum + Regime + كل أنظمة الحماية")
    print("  الاختبار الحاسم مباشرةً: 4 شرائح زمنية × 5 أزواج")
    print("=" * 64)

    folds = {f: [] for f in range(4)}
    stats = {"trades": 0, "blocked": 0, "kills": 0}
    for s in cfg.SYMBOLS:
        df = prepare(fetch_history(s, total=5000))
        df = detect_regime(df)
        df = df.iloc[250:].reset_index(drop=True)
        fs = len(df) // 4
        for f in range(4):
            chunk = df.iloc[f * fs:(f + 1) * fs].reset_index(drop=True)
            ret, tr, wr, blk, killed = simulate_fortress(chunk)
            folds[f].append(ret)
            stats["trades"] += tr
            stats["blocked"] += blk
            stats["kills"] += killed
        print(f"  ✓ {s}")

    print()
    allr = []
    for f in range(4):
        r = folds[f]
        allr += r
        w = sum(1 for x in r if x > 0)
        flag = "✅" if np.mean(r) > 0 else "❌"
        print(f"  الشريحة {f+1}: متوسط {np.mean(r):+7.2f}% | رابحة {w}/5  {flag}")
    print("=" * 64)
    pos_folds = sum(1 for f in range(4) if np.mean(folds[f]) > 0)
    print(f"  المتوسط الكلي : {np.mean(allr):+.2f}% | شرائح رابحة: {pos_folds}/4")
    print(f"  الانحراف      : {np.std(allr):.1f}% (كان ±18.4% بلا حماية)")
    print(f"  صفقات منفّذة  : {stats['trades']} | صفقات حجبتها الحماية: {stats['blocked']}")
    print(f"  تفعيلات Kill Switch: {stats['kills']}")
    print("=" * 64)
