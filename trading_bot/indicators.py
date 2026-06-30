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


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """مؤشر متوسط الحركة الاتجاهية — يقيس قوة الاتجاه (لا اتجاهه)."""
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr_ = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_.replace(0, 1e-10)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_.replace(0, 1e-10)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
    return dx.ewm(alpha=1 / period, adjust=False).mean()


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """إضافة كل المؤشرات المطلوبة للاستراتيجية إلى DataFrame."""
    df = df.copy()
    df["ema_fast"] = ema(df["close"], cfg.EMA_FAST)
    df["ema_slow"] = ema(df["close"], cfg.EMA_SLOW)
    df["ema_trend_fast"] = ema(df["close"], cfg.EMA_TREND_FAST)
    df["ema_trend_slow"] = ema(df["close"], cfg.EMA_TREND_SLOW)
    df["rsi"] = rsi(df["close"], cfg.RSI_PERIOD)
    df["atr"] = atr(df, cfg.ATR_PERIOD)
    df["adx"] = adx(df, cfg.ADX_PERIOD)
    df["vol_ma"] = df["vol"].rolling(cfg.VOLUME_MA_PERIOD).mean()
    return df
