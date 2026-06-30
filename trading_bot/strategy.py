"""
منطق الاستراتيجية: استراتيجية اتجاهية متعددة الطبقات للتأكيد.

شروط الدخول (شراء):
  1. الاتجاه العام صاعد:   EMA(50) > EMA(200)
  2. تقاطع الدخول:         EMA(9) يتقاطع صعودًا فوق EMA(21)
  3. الزخم سليم:           RSI بين الحد الأدنى وحد التشبّع
  4. تأكيد الحجم:          حجم الشمعة أعلى من متوسطه

الخروج يُدار عبر وقف الخسارة / جني الأرباح / الوقف المتحرك
(تُحسب في محرّك الاختبار أو منفّذ الصفقات).
"""


def _crossed_up(prev_fast, prev_slow, fast, slow):
    """هل تقاطع المتوسط السريع صعودًا فوق البطيء في هذه الشمعة؟"""
    return prev_fast <= prev_slow and fast > slow


def _crossed_down(prev_fast, prev_slow, fast, slow):
    """هل تقاطع المتوسط السريع هبوطًا تحت البطيء في هذه الشمعة؟"""
    return prev_fast >= prev_slow and fast < slow


def entry_signal(df, i, cfg):
    """
    تقييم شمعة عند الفهرس i.
    يعيد:  1 لإشارة شراء (Long)، -1 لإشارة بيع (Short)، 0 لا إشارة.
    يتطلب شمعة سابقة (i-1) لاكتشاف التقاطع.
    """
    if i < 1:
        return 0

    row = df.iloc[i]
    prev = df.iloc[i - 1]

    # تجاهل الصفوف التي لم تكتمل مؤشراتها بعد
    required = ["ema_fast", "ema_slow", "ema_trend_fast",
                "ema_trend_slow", "rsi", "atr", "adx", "vol_ma"]
    if any(pd.isna(row[c]) for c in required):
        return 0

    # فلاتر مشتركة للاتجاهين
    volume_ok = row["vol"] > row["vol_ma"]
    strong_trend = row["adx"] >= cfg.ADX_MIN
    if not (volume_ok and strong_trend):
        return 0

    # ---- إشارة شراء (Long) ----
    trend_up = row["ema_trend_fast"] > row["ema_trend_slow"]
    cross_up = _crossed_up(prev["ema_fast"], prev["ema_slow"],
                           row["ema_fast"], row["ema_slow"])
    long_momentum = cfg.RSI_LOWER <= row["rsi"] <= cfg.RSI_UPPER
    if trend_up and cross_up and long_momentum:
        return 1

    # ---- إشارة بيع (Short) — انعكاس متماثل للمنطق ----
    if cfg.ALLOW_SHORT:
        trend_down = row["ema_trend_fast"] < row["ema_trend_slow"]
        cross_down = _crossed_down(prev["ema_fast"], prev["ema_slow"],
                                   row["ema_fast"], row["ema_slow"])
        # في الهبوط: RSI بين حد التشبّع البيعي والمنتصف
        short_momentum = (100 - cfg.RSI_UPPER) <= row["rsi"] <= (100 - cfg.RSI_LOWER)
        if trend_down and cross_down and short_momentum:
            return -1

    return 0


def compute_stops(entry_price, atr_value, direction, cfg):
    """
    حساب وقف الخسارة وجني الأرباح حسب اتجاه الصفقة.
    direction = 1 شراء، -1 بيع.
    """
    risk = atr_value * cfg.ATR_STOP_MULTIPLIER
    if direction == 1:
        stop_loss = entry_price - risk
        take_profit = entry_price + risk * cfg.RISK_REWARD_RATIO
    else:
        stop_loss = entry_price + risk
        take_profit = entry_price - risk * cfg.RISK_REWARD_RATIO
    return stop_loss, take_profit


def position_size(capital, entry_price, stop_loss, cfg):
    """
    حجم الصفقة بحيث لا تتجاوز الخسارة المحتملة نسبة المخاطرة المحددة.
    يعيد الكمية (بالعملة الأساسية). يعمل للاتجاهين عبر القيمة المطلقة.
    """
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0:
        return 0.0
    capital_at_risk = capital * cfg.RISK_PER_TRADE
    qty = capital_at_risk / risk_per_unit
    return qty


# استيراد متأخّر لتجنّب الاعتماد عند الاستخدام المنطقي البحت
import pandas as pd  # noqa: E402
