"""
استراتيجية ICT / SMC (Smart Money Concepts).

تطبيق مبسّط لكنه أمين لأهم مفاهيم "المال الذكي":

  • هيكل السوق (Market Structure): نقاط التأرجح (Swing Highs/Lows).
  • كسر الهيكل (BOS - Break of Structure): إغلاق فوق آخر قمة (صعود)
    أو تحت آخر قاع (هبوط) — يدل على استمرار الاتجاه.
  • فجوة القيمة العادلة (FVG - Fair Value Gap): عدم توازن من 3 شموع
    حيث يترك السعر فراغًا يميل للعودة لملئه.

⚠️ ملاحظة منهجية: كل الحسابات سببية (causal) — لا تستخدم أي بيانات
مستقبلية. نقطة التأرجح لا تُعتمد إلا بعد تأكيدها بشموع لاحقة.

إشارة الدخول:
  شراء  = كسر هيكل صاعد (BOS up) + وجود فجوة قيمة عادلة صاعدة.
  بيع   = كسر هيكل هابط (BOS down) + وجود فجوة قيمة عادلة هابطة.
"""
import numpy as np
import pandas as pd


def add_smc(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """إضافة أعمدة SMC: نقاط التأرجح المؤكّدة، كسر الهيكل، وفجوات القيمة العادلة."""
    df = df.copy().reset_index(drop=True)
    n = len(df)
    k = cfg.SWING_LOOKBACK

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    last_swing_high = np.full(n, np.nan)
    last_swing_low = np.full(n, np.nan)

    run_sh = np.nan
    run_sl = np.nan
    for i in range(n):
        # عند الوصول إلى i، يمكن تأكيد نقطة تأرجح عند p = i-k
        p = i - k
        if p - k >= 0:
            window_h = high[p - k:i + 1]
            window_l = low[p - k:i + 1]
            if high[p] == window_h.max():
                run_sh = high[p]
            if low[p] == window_l.min():
                run_sl = low[p]
        last_swing_high[i] = run_sh
        last_swing_low[i] = run_sl

    df["last_swing_high"] = last_swing_high
    df["last_swing_low"] = last_swing_low

    # كسر الهيكل (يُحسب من الإغلاق مقابل آخر نقطة تأرجح مؤكّدة)
    df["bos_up"] = close > last_swing_high
    df["bos_down"] = close < last_swing_low

    # فجوة القيمة العادلة (نمط 3 شموع: i-2, i-1, i)
    h2 = df["high"].shift(2)
    l2 = df["low"].shift(2)
    df["fvg_bull"] = df["low"] > h2     # فراغ صاعد: قاع الشمعة الحالية فوق قمة شمعة قبل شمعتين
    df["fvg_bear"] = df["high"] < l2    # فراغ هابط: قمة الشمعة الحالية تحت قاع شمعة قبل شمعتين

    return df


def entry_signal_smc(df, i, cfg):
    """إشارة SMC عند الفهرس i: 1 شراء، -1 بيع، 0 لا شيء."""
    if i < 1:
        return 0
    row = df.iloc[i]

    required = ["last_swing_high", "last_swing_low", "atr"]
    if any(pd.isna(row[c]) for c in required):
        return 0

    # فلتر تقلّب أدنى (نتجنّب الشموع الميتة)
    if row["atr"] <= 0:
        return 0

    bull = bool(row["bos_up"]) and bool(row["fvg_bull"])
    if bull:
        return 1

    if cfg.ALLOW_SHORT:
        bear = bool(row["bos_down"]) and bool(row["fvg_bear"])
        if bear:
            return -1

    return 0
