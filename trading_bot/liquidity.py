"""
[7] Liquidity Analysis System — نظام تحليل السيولة.

يكتشف مناطق السيولة التي يستهدفها "المال الذكي":
  • القمم/القيعان المتساوية (Equal Highs/Lows): تجمّعات أوامر وقف.
  • اكتساح السيولة (Liquidity Sweep): اختراق قمة/قاع سابق ثم الانعكاس
    — إشارة كلاسيكية على أن المؤسسات جمعت السيولة قبل التحرّك المعاكس.
  • ارتفاعات الحجم (Volume Spikes): دليل على نشاط مؤسسي.
"""
import numpy as np
import pandas as pd


def add_liquidity(df: pd.DataFrame, lookback=20, tol=0.001) -> pd.DataFrame:
    """إضافة أعمدة تحليل السيولة."""
    df = df.copy().reset_index(drop=True)
    high, low = df["high"], df["low"]

    # أعلى قمة / أدنى قاع خلال فترة سابقة (سيولة معلّقة)
    prior_high = high.rolling(lookback).max().shift(1)
    prior_low = low.rolling(lookback).min().shift(1)

    # اكتساح السيولة: تجاوز القمة السابقة ثم الإغلاق تحتها (sweep علوي = هبوطي)
    df["sweep_high"] = (high > prior_high) & (df["close"] < prior_high)
    # اكتساح القاع السابق ثم الإغلاق فوقه (sweep سفلي = صعودي)
    df["sweep_low"] = (low < prior_low) & (df["close"] > prior_low)

    # ارتفاع الحجم
    vol_ma = df["vol"].rolling(20).mean()
    df["vol_spike"] = df["vol"] > vol_ma * 1.5

    # قمم/قيعان متساوية (تجمّع سيولة)
    df["equal_high"] = (high - prior_high).abs() / df["close"] < tol
    df["equal_low"] = (low - prior_low).abs() / df["close"] < tol

    return df


def liquidity_signal(df, i):
    """إشارة مبنية على اكتساح السيولة + تأكيد الحجم. 1 شراء، -1 بيع، 0 لا شيء."""
    if i < 1 or "sweep_low" not in df.columns:
        return 0
    row = df.iloc[i]
    if bool(row.get("sweep_low")) and bool(row.get("vol_spike")):
        return 1   # اكتُسحت سيولة القاع بحجم → انعكاس صعودي محتمل
    if bool(row.get("sweep_high")) and bool(row.get("vol_spike")):
        return -1  # اكتُسحت سيولة القمة بحجم → انعكاس هبوطي محتمل
    return 0
