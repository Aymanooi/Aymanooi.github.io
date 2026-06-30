"""
هندسة الخصائص (Feature Engineering) للتعلّم الآلي.

نحوّل بيانات الشموع الخام إلى مصفوفة خصائص رقمية يتعلّم منها النموذج.

⚠️ قاعدة ذهبية لتجنّب تسرّب البيانات (Data Leakage):
كل خاصية يجب أن تُحسب من بيانات *الماضي والحاضر فقط* — لا يُسمح أبدًا
باستخدام أي معلومة من المستقبل. لذلك:
  - الخصائص (X): تُحسب من الشمعة الحالية والسابقة.
  - الهدف (y): عائد الشمعة *القادمة* — وهو ما نحاول التنبؤ به.
"""
import numpy as np
import pandas as pd

from indicators import ema, rsi, atr, adx, macd, bollinger, stochastic


def build_features(df: pd.DataFrame, horizon: int = 1, target_threshold: float = 0.0):
    """
    بناء مصفوفة الخصائص X والهدف y.

    horizon: عدد الشموع المستقبلية التي نتنبأ بعائدها.
    target_threshold: عتبة العائد لاعتباره "صعودًا" (1) وإلا (0).

    يعيد (X, y, feature_names, df_aligned).
    """
    df = df.copy().reset_index(drop=True)
    close = df["close"]

    feat = pd.DataFrame(index=df.index)

    # --- خصائص العائد (Momentum) على آفاق متعددة ---
    for n in [1, 2, 3, 5, 8, 13]:
        feat[f"ret_{n}"] = close.pct_change(n)

    # --- التقلّب (Volatility) ---
    feat["volatility_5"] = close.pct_change().rolling(5).std()
    feat["volatility_10"] = close.pct_change().rolling(10).std()
    atr_ = atr(df, 14)
    feat["atr_pct"] = atr_ / close  # ATR كنسبة من السعر

    # --- مؤشرات الزخم ---
    feat["rsi"] = rsi(close, 14)
    feat["rsi_norm"] = (feat["rsi"] - 50) / 50  # مركزة حول الصفر
    k, d = stochastic(df, 14, 3)
    feat["stoch_k"] = k
    feat["stoch_d"] = d
    feat["stoch_diff"] = k - d

    # --- الاتجاه ---
    ema_fast = ema(close, 9)
    ema_slow = ema(close, 21)
    ema_trend = ema(close, 50)
    feat["ema_fast_dist"] = (close - ema_fast) / close
    feat["ema_slow_dist"] = (close - ema_slow) / close
    feat["ema_cross"] = (ema_fast - ema_slow) / close
    feat["ema_trend_dist"] = (close - ema_trend) / close
    feat["adx"] = adx(df, 14)

    # --- MACD ---
    macd_line, signal_line, hist = macd(close)
    feat["macd"] = macd_line / close
    feat["macd_hist"] = hist / close

    # --- نطاقات بولينجر (الموقع داخل النطاق) ---
    upper, mid, lower = bollinger(close, 20, 2.0)
    feat["bb_position"] = (close - lower) / (upper - lower).replace(0, 1e-10)

    # --- الحجم ---
    feat["vol_ratio"] = df["vol"] / df["vol"].rolling(20).mean()

    # --- خصائص زمنية (هل للوقت تأثير؟) ---
    feat["hour"] = df["ts"].dt.hour
    feat["dayofweek"] = df["ts"].dt.dayofweek

    # ===== الهدف (y): عائد الشمعة القادمة =====
    future_ret = close.shift(-horizon) / close - 1
    y = (future_ret > target_threshold).astype(int)

    # نحفظ العائد المستقبلي الفعلي لاستخدامه في الاختبار المالي لاحقًا
    feat["_future_ret"] = future_ret

    # حذف الصفوف ذات القيم الناقصة (بداية المؤشرات ونهاية الهدف)
    feature_names = [c for c in feat.columns if not c.startswith("_")]
    combined = feat.copy()
    combined["_y"] = y
    combined["_ts"] = df["ts"]
    combined = combined.dropna().reset_index(drop=True)

    X = combined[feature_names]
    y = combined["_y"]
    return X, y, feature_names, combined


if __name__ == "__main__":
    from data_feed import fetch_history
    df = fetch_history("BTC-USDT", total=1000)
    X, y, names, _ = build_features(df)
    print(f"عدد الخصائص: {len(names)}")
    print(f"عدد العيّنات: {len(X)}")
    print(f"توزيع الهدف: صعود={y.sum()} ({y.mean()*100:.1f}%) | هبوط={len(y)-y.sum()}")
    print("الخصائص:", names)
