"""
المؤشرات الفنية المحسوبة يدويًا (دون مكتبات خارجية ثقيلة).
كلها تعتمد على pandas/numpy فقط.
"""
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """المتوسط المتحرك الأسّي."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """مؤشر القوة النسبية (Wilder's RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # تنعيم Wilder (مكافئ لـ ewm مع alpha = 1/period)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """متوسط المدى الحقيقي — مقياس التقلّب لتحديد وقف الخسارة."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """إضافة كل المؤشرات المطلوبة للاستراتيجية إلى DataFrame."""
    df = df.copy()
    df["ema_fast"] = ema(df["close"], cfg.EMA_FAST)
    df["ema_slow"] = ema(df["close"], cfg.EMA_SLOW)
    df["ema_trend_fast"] = ema(df["close"], cfg.EMA_TREND_FAST)
    df["ema_trend_slow"] = ema(df["close"], cfg.EMA_TREND_SLOW)
    df["rsi"] = rsi(df["close"], cfg.RSI_PERIOD)
    df["atr"] = atr(df, cfg.ATR_PERIOD)
    df["vol_ma"] = df["vol"].rolling(cfg.VOLUME_MA_PERIOD).mean()
    return df
