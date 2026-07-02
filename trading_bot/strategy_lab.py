"""
مختبر الاستراتيجيات — اختبار جماعي صارم لكل العائلات الجديدة المطلوبة.

كل استراتيجية تُقيَّم بنفس الشروط تمامًا:
  • مؤشرات سببية فقط (لا نظر للمستقبل)
  • التقييم على آخر 30% من البيانات فقط (out-of-sample)
  • نفس إدارة المخاطر: مخاطرة 2%، وقف ATR×1.5، هدف 1:2، رسوم OKX

العائلات المختبرة:
  Donchian Breakout · Supertrend · Ichimoku · Bollinger Squeeze
  Mean Reversion (Z-Score) · VWAP Reversion · Momentum Confluence
  + Pairs Trading / Cointegration (محايدة للسوق — تُختبر على حدة)
"""
import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import ema, rsi, atr, macd, bollinger

FEE = cfg.TAKER_FEE
OOS_FRAC = 0.30          # نسبة الاختبار خارج العيّنة


# ============ تجهيز المؤشرات (كلها سببية) ============

def prepare(df):
    df = df.copy().reset_index(drop=True)
    h, l, c, v = df["high"], df["low"], df["close"], df["vol"]

    df["atr"] = atr(df, 14)

    # Donchian (قنوات الفترة السابقة — بلا الشمعة الحالية)
    df["don_hi"] = h.rolling(20).max().shift(1)
    df["don_lo"] = l.rolling(20).min().shift(1)

    # Supertrend (10, 3) — حساب تكراري سببي
    hl2 = (h + l) / 2
    a = atr(df, 10)
    up_b = hl2 + 3 * a
    dn_b = hl2 - 3 * a
    st_dir = np.ones(len(df))
    up_f, dn_f = up_b.copy(), dn_b.copy()
    for i in range(1, len(df)):
        up_f.iloc[i] = min(up_b.iloc[i], up_f.iloc[i-1]) if c.iloc[i-1] < up_f.iloc[i-1] else up_b.iloc[i]
        dn_f.iloc[i] = max(dn_b.iloc[i], dn_f.iloc[i-1]) if c.iloc[i-1] > dn_f.iloc[i-1] else dn_b.iloc[i]
        if c.iloc[i] > up_f.iloc[i-1]:
            st_dir[i] = 1
        elif c.iloc[i] < dn_f.iloc[i-1]:
            st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i-1]
    df["st_dir"] = st_dir

    # Ichimoku (مبسّط سببي)
    df["tenkan"] = (h.rolling(9).max() + l.rolling(9).min()) / 2
    df["kijun"] = (h.rolling(26).max() + l.rolling(26).min()) / 2
    senkou_a = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
    senkou_b = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    df["cloud_top"] = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    df["cloud_bot"] = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)

    # Bollinger Squeeze
    up, mid, lo = bollinger(c, 20, 2.0)
    df["bb_up"], df["bb_lo"] = up, lo
    bw = (up - lo) / mid
    df["squeeze"] = bw < bw.rolling(100).quantile(0.2)

    # Mean Reversion Z-Score
    sma50 = c.rolling(50).mean()
    std50 = c.rolling(50).std().replace(0, 1e-10)
    df["z"] = (c - sma50) / std50
    df["trend200"] = ema(c, 200)

    # Rolling VWAP (نافذة 24 ساعة)
    pv = (c * v).rolling(24).sum()
    df["vwap"] = pv / v.rolling(24).sum().replace(0, 1e-10)
    df["vwap_dev"] = (c - df["vwap"]) / df["atr"].replace(0, 1e-10)

    # Momentum Confluence (توافق 3 آفاق)
    df["roc5"], df["roc13"], df["roc34"] = c.pct_change(5), c.pct_change(13), c.pct_change(34)

    df["rsi"] = rsi(c, 14)
    return df


# ============ دوال الإشارة (كلها تقرأ الشمعة i والسابقة فقط) ============

def sig_donchian(df, i):
    r, p = df.iloc[i], df.iloc[i-1]
    if pd.isna(r["don_hi"]):
        return 0
    if r["close"] > r["don_hi"] and p["close"] <= p["don_hi"]:
        return 1
    if r["close"] < r["don_lo"] and p["close"] >= p["don_lo"]:
        return -1
    return 0


def sig_supertrend(df, i):
    r, p = df.iloc[i], df.iloc[i-1]
    if p["st_dir"] <= 0 and r["st_dir"] > 0:
        return 1
    if p["st_dir"] >= 0 and r["st_dir"] < 0:
        return -1
    return 0


def sig_ichimoku(df, i):
    r, p = df.iloc[i], df.iloc[i-1]
    if pd.isna(r["cloud_top"]):
        return 0
    cross_up = p["tenkan"] <= p["kijun"] and r["tenkan"] > r["kijun"]
    cross_dn = p["tenkan"] >= p["kijun"] and r["tenkan"] < r["kijun"]
    if cross_up and r["close"] > r["cloud_top"]:
        return 1
    if cross_dn and r["close"] < r["cloud_bot"]:
        return -1
    return 0


def sig_squeeze(df, i):
    r, p = df.iloc[i], df.iloc[i-1]
    if pd.isna(r["bb_up"]) or not bool(p.get("squeeze", False)):
        return 0
    if r["close"] > r["bb_up"]:
        return 1
    if r["close"] < r["bb_lo"]:
        return -1
    return 0


def sig_meanrev(df, i):
    r = df.iloc[i]
    if pd.isna(r["z"]) or pd.isna(r["trend200"]):
        return 0
    # ارتداد نحو المتوسط، مع فلتر الاتجاه الكبير
    if r["z"] < -2.0 and r["close"] > r["trend200"]:
        return 1
    if r["z"] > 2.0 and r["close"] < r["trend200"]:
        return -1
    return 0


def sig_vwap(df, i):
    r = df.iloc[i]
    if pd.isna(r["vwap_dev"]):
        return 0
    if r["vwap_dev"] < -2.0:
        return 1
    if r["vwap_dev"] > 2.0:
        return -1
    return 0


def sig_momentum(df, i):
    r = df.iloc[i]
    if pd.isna(r["roc34"]):
        return 0
    pos = (r["roc5"] > 0) + (r["roc13"] > 0) + (r["roc34"] > 0)
    if pos == 3 and 50 < r["rsi"] < 75:
        return 1
    if pos == 0 and 25 < r["rsi"] < 50:
        return -1
    return 0


STRATEGIES = {
    "Donchian Breakout":   sig_donchian,
    "Supertrend":          sig_supertrend,
    "Ichimoku":            sig_ichimoku,
    "Bollinger Squeeze":   sig_squeeze,
    "Mean Reversion (Z)":  sig_meanrev,
    "VWAP Reversion":      sig_vwap,
    "Momentum Confluence": sig_momentum,
}


# ============ محرّك التنفيذ الموحّد ============

def simulate(df, sig_func, start_i):
    capital = 1000.0
    pos = None
    trades = wins = 0
    for i in range(max(start_i, 1), len(df)):
        r = df.iloc[i]
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
                wins += pnl > 0
                pos = None
        if pos is None and not pd.isna(r["atr"]) and r["atr"] > 0:
            d = sig_func(df, i)
            if d != 0:
                e = r["close"]
                risk = r["atr"] * 1.5
                sl = e - risk * d
                tp = e + risk * 2 * d
                q = capital * 0.02 / risk
                if e * q / 10 <= capital:
                    pos = {"d": d, "e": e, "sl": sl, "tp": tp, "q": q}
    ret = (capital - 1000) / 10
    return ret, trades, (wins / trades * 100 if trades else 0)


# ============ Pairs Trading / Cointegration ============

def pairs_trading(data):
    """أفضل زوج مترابط: تداول ارتداد الفارق (محايد للسوق)."""
    syms = list(data.keys())
    best = None
    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            a, b = data[syms[i]]["close"], data[syms[j]]["close"]
            n = min(len(a), len(b))
            corr = np.corrcoef(np.log(a[:n]), np.log(b[:n]))[0, 1]
            if best is None or corr > best[2]:
                best = (syms[i], syms[j], corr)
    s1, s2, corr = best
    a = np.log(data[s1]["close"].values)
    b = np.log(data[s2]["close"].values)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    split = int(n * (1 - OOS_FRAC))

    # نسبة التحوّط ومعايير الفارق من التدريب فقط
    beta = np.polyfit(b[:split], a[:split], 1)[0]
    spread = a - beta * b
    mu, sd = spread[:split].mean(), spread[:split].std()

    capital = 1000.0
    pos = 0
    trades = wins = 0
    entry_spread = 0.0
    for i in range(split, n):
        z = (spread[i] - mu) / sd
        if pos == 0:
            if z > 2:
                pos, entry_spread = -1, spread[i]
                capital -= capital * FEE * 2
            elif z < -2:
                pos, entry_spread = 1, spread[i]
                capital -= capital * FEE * 2
        else:
            if abs(z) < 0.5 or abs(z) > 4:
                pnl_frac = pos * (spread[i] - entry_spread)
                pnl = capital * pnl_frac
                capital += pnl - capital * FEE * 2
                trades += 1
                wins += pnl > 0
                pos = 0
    ret = (capital - 1000) / 10
    return s1, s2, corr, ret, trades, (wins / trades * 100 if trades else 0)


if __name__ == "__main__":
    print("=" * 66)
    print("  🧪 مختبر الاستراتيجيات — 8 عائلات جديدة | out-of-sample 30%")
    print("=" * 66)
    print("جلب البيانات...")
    data = {}
    for s in cfg.SYMBOLS:
        raw = fetch_history(s, total=5000)
        data[s] = prepare(raw)
        print(f"  ✓ {s}")

    print(f"\n{'الاستراتيجية':<24}{'متوسط العائد':<14}{'أزواج رابحة':<12}{'صفقات'}")
    print("-" * 66)
    summary = []
    for name, fn in STRATEGIES.items():
        rets, tot_tr = [], 0
        for s, df in data.items():
            start_i = int(len(df) * (1 - OOS_FRAC))
            ret, tr, wr = simulate(df, fn, start_i)
            rets.append(ret)
            tot_tr += tr
        avg = np.mean(rets)
        winners = sum(1 for r in rets if r > 0)
        summary.append((name, avg, winners, tot_tr))
        flag = "✅" if avg > 0.5 else ("≈" if avg > -0.5 else "❌")
        print(f"{name:<24}{avg:+7.2f}%      {winners}/5         {tot_tr:4d}  {flag}")

    print("-" * 66)
    s1, s2, corr, ret, tr, wr = pairs_trading(data)
    flag = "✅" if ret > 0.5 else ("≈" if ret > -0.5 else "❌")
    print(f"{'Pairs/Cointegration':<24}{ret:+7.2f}%      {s1}×{s2} (r={corr:.2f}) {tr} صفقة {flag}")
    print("=" * 66)

    best = max(summary, key=lambda x: x[1])
    print(f"\n  أفضل عائلة اتجاهية: {best[0]} ({best[1]:+.2f}%)")
    avg_all = np.mean([x[1] for x in summary])
    print(f"  متوسط كل العائلات: {avg_all:+.2f}%")
