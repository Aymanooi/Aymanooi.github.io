"""
محرّك النقاط "المؤسسي" — من بوت المستخدم السادس (INSTITUTIONAL AI SYSTEM).

يُدمج في FUSION كبوابة تأكيد إضافية: الإشارة المرشّحة يجب أن تجتاز
درجة النقاط المركّبة (قواعد + نموذج ML خفيف) قبل التنفيذ.

مكوّنات الدرجة (كما صمّمها المالك، مع انعكاس للبيع):
  0.3  اتجاه EMA9/EMA21
  0.2  زخم RSI حول 50
  0.2  الموقع من EMA50
  0.3  تنبؤ RandomForest (احتمال اتجاه 3 شموع قادمة)
  عقوبة -0.15 في نظام التقلب العالي
  العتبة: 0.78 (إجماع شبه كامل)

⚠️ توثيق منهجي: نموذج RF يُدرَّب على نافذة البيانات الحية نفسها في
كل دورة (تصميم المالك الأصلي). هذا يجعل مساهمته أقرب لمؤشر زخم
تكيّفي منه لتنبؤ معمَّم — مساهمته محدودة بـ 0.3 من الدرجة والقرار
النهائي محكوم ببقية بوابات FUSION المدقّقة.
"""
import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestClassifier
    SK = True
except ImportError:
    SK = False

from indicators import ema, rsi

MIN_SCORE = 0.78
VOL_PENALTY = 0.15


def _features(df):
    close = df["close"]
    f = pd.DataFrame({
        "ret": close.pct_change(),
        "ema9": ema(close, 9),
        "ema21": ema(close, 21),
        "rsi": rsi(close, 14),
        "vol": df["vol"],
    })
    return f.dropna()


def _ml_proba(df):
    """تدريب/تنبؤ RF بأسلوب المالك (نافذة حية، آخر 10 صفوف خارج التدريب)."""
    if not SK:
        return 0.5
    f = _features(df)
    if len(f) < 50:
        return 0.5
    target = (df["close"].shift(-3) > df["close"]).astype(int)
    y = target.loc[f.index]
    X = f[["ret", "ema9", "ema21", "rsi", "vol"]]
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=7)
    model.fit(X.iloc[:-10], y.iloc[:-10])
    return float(model.predict_proba(X.iloc[[-1]])[0][1])


def institutional_score(df, direction):
    """درجة النقاط للاتجاه المطلوب (1 شراء / -1 بيع). تعيد [0..1]."""
    close = df["close"]
    e9 = ema(close, 9).iloc[-1]
    e21 = ema(close, 21).iloc[-1]
    e50 = ema(close, 50).iloc[-1]
    r = rsi(close, 14).iloc[-1]
    ml = _ml_proba(df)

    s = 0.0
    if direction == 1:
        if e9 > e21:
            s += 0.3
        if r > 50:
            s += 0.2
        if close.iloc[-1] > e50:
            s += 0.2
        if ml > 0.55:
            s += 0.3
    else:
        if e9 < e21:
            s += 0.3
        if r < 50:
            s += 0.2
        if close.iloc[-1] < e50:
            s += 0.2
        if ml < 0.45:
            s += 0.3

    # عقوبة نظام التقلب العالي (تصميم المالك)
    if close.pct_change().std() > 0.04:
        s -= VOL_PENALTY

    return max(0.0, min(s, 1.0))


def passes_gate(df, direction, min_score=MIN_SCORE):
    """هل تجتاز الإشارة البوابة المؤسسية؟ تعيد (نجاح, الدرجة)."""
    s = institutional_score(df, direction)
    return s >= min_score, s
