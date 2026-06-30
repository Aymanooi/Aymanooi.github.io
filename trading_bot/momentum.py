"""
[6] Multi-Factor Momentum Strategy — استراتيجية الزخم متعدد العوامل.

بدلًا من عامل واحد، تدمج عدة عوامل زخم في درجة موحّدة (z-score):
  • معدّل التغيّر (ROC) على آفاق متعددة.
  • زخم MACD (الهيستوجرام).
  • قوة RSI المركزة.
  • قوة الاتجاه (نسبة بُعد السعر عن متوسطه).

إشارة قوية = توافق عدة عوامل في نفس الاتجاه.
"""
import numpy as np
import pandas as pd

from indicators import ema, rsi, macd


def _zscore(series, window=100):
    mean = series.rolling(window).mean()
    std = series.rolling(window).std().replace(0, 1e-10)
    return (series - mean) / std


def add_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """إضافة درجة الزخم المركّبة 'mom_score'."""
    df = df.copy().reset_index(drop=True)
    close = df["close"]

    roc_short = close.pct_change(5)
    roc_mid = close.pct_change(13)
    roc_long = close.pct_change(34)
    _, _, hist = macd(close)
    rsi_c = (rsi(close, 14) - 50) / 50
    ema_dist = (close - ema(close, 50)) / close

    # توحيد كل عامل ثم جمعها بأوزان متساوية
    factors = pd.DataFrame({
        "roc_s": _zscore(roc_short),
        "roc_m": _zscore(roc_mid),
        "roc_l": _zscore(roc_long),
        "macd": _zscore(hist),
        "rsi": _zscore(rsi_c),
        "ema": _zscore(ema_dist),
    })
    df["mom_score"] = factors.mean(axis=1)
    return df


def momentum_signal(df, i, threshold=0.7):
    """إشارة الزخم: 1 إذا الدرجة موجبة قوية، -1 إذا سالبة قوية، 0 غير ذلك."""
    if "mom_score" not in df.columns:
        return 0
    score = df["mom_score"].iloc[i]
    if pd.isna(score):
        return 0
    if score >= threshold:
        return 1
    if score <= -threshold:
        return -1
    return 0
