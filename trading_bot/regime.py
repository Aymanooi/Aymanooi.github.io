"""
[1] Market Regime Detection — كشف نظام السوق.

يصنّف السوق في كل لحظة إلى أحد الأنظمة:
  • TREND_UP    : اتجاه صاعد قوي
  • TREND_DOWN  : اتجاه هابط قوي
  • RANGE       : سوق عرضي متذبذب (بلا اتجاه)
  • HIGH_VOL    : تقلّب مرتفع خطر

أساس التصنيف: قوة الاتجاه (ADX) + اتجاه المتوسطات + نسبة التقلّب (ATR%).
معرفة النظام تتيح للمنسّق اختيار الاستراتيجية المناسبة لكل بيئة.
"""
import numpy as np
import pandas as pd

from indicators import ema, adx, atr

TREND_UP = "TREND_UP"
TREND_DOWN = "TREND_DOWN"
RANGE = "RANGE"
HIGH_VOL = "HIGH_VOL"


def detect_regime(df: pd.DataFrame, adx_min=22, vol_quantile=0.85) -> pd.DataFrame:
    """إضافة عمود 'regime' وعمود 'atr_pct' و'adx_r' للـ DataFrame."""
    df = df.copy().reset_index(drop=True)
    close = df["close"]

    ema_fast = ema(close, 50)
    ema_slow = ema(close, 200)
    adx_v = adx(df, 14)
    atr_v = atr(df, 14)
    atr_pct = atr_v / close

    # عتبة التقلّب المرتفع: أعلى من النسبة المئوية التاريخية
    vol_threshold = atr_pct.expanding(min_periods=50).quantile(vol_quantile)

    regimes = []
    for i in range(len(df)):
        a = adx_v.iloc[i]
        ap = atr_pct.iloc[i]
        vt = vol_threshold.iloc[i]
        if pd.isna(a) or pd.isna(ema_slow.iloc[i]):
            regimes.append(RANGE)
            continue
        if not pd.isna(vt) and ap > vt and a < adx_min:
            regimes.append(HIGH_VOL)   # تقلّب عالٍ بلا اتجاه = خطر
        elif a >= adx_min and ema_fast.iloc[i] > ema_slow.iloc[i]:
            regimes.append(TREND_UP)
        elif a >= adx_min and ema_fast.iloc[i] < ema_slow.iloc[i]:
            regimes.append(TREND_DOWN)
        else:
            regimes.append(RANGE)

    df["regime"] = regimes
    df["atr_pct"] = atr_pct
    df["adx_r"] = adx_v
    return df


if __name__ == "__main__":
    from data_feed import fetch_history
    df = detect_regime(fetch_history("BTC-USDT", total=1500))
    print(df["regime"].value_counts())
