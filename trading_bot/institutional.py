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
    from sklearn.linear_model import SGDClassifier
    from sklearn.preprocessing import StandardScaler
    SK = True
except ImportError:
    SK = False

from indicators import ema, rsi

MIN_SCORE = 0.80          # V2: عتبة أعلى
VOL_PENALTY = 0.15
CHAOS_VOL = 0.05          # V2: فوق هذا التقلب = فوضى، لا تداول


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
    """
    V2: Ensemble من نموذجين (RF 0.6 + SGD 0.4) مع معايرة StandardScaler.
    يُدرَّب على نافذة الرمز الحية (تصميم المالك، بإصلاح: لكل رمز نموذجه
    بدل نموذج واحد مدرَّب على أول رمز فقط كما في الأصل).
    """
    if not SK:
        return 0.5
    f = _features(df)
    if len(f) < 50:
        return 0.5
    target = (df["close"].shift(-3) > df["close"]).astype(int)
    y = target.loc[f.index]
    X = f[["ret", "ema9", "ema21", "rsi", "vol"]]
    X_tr, y_tr = X.iloc[:-5], y.iloc[:-5]
    if y_tr.nunique() < 2:
        return 0.5
    scaler = StandardScaler().fit(X_tr)
    Xs = scaler.transform(X_tr)
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=7)
    rf.fit(Xs, y_tr)
    sgd = SGDClassifier(loss="log_loss", random_state=7)
    sgd.partial_fit(Xs, y_tr, classes=[0, 1])
    x_last = scaler.transform(X.iloc[[-1]])
    p1 = float(rf.predict_proba(x_last)[0][1])
    p2 = float(sgd.predict_proba(x_last)[0][1])
    return p1 * 0.6 + p2 * 0.4


def institutional_score(df, direction):
    """
    درجة V2 للاتجاه المطلوب (1 شراء / -1 بيع). تعيد [0..1].
    مساهمة ML متصلة (ml × 0.3) كما في V2، مع حارس الفوضى.
    """
    close = df["close"]
    vol_std = close.pct_change().std()
    # V2: نظام الفوضى = لا تداول إطلاقًا
    if vol_std > CHAOS_VOL:
        return 0.0

    e9 = ema(close, 9).iloc[-1]
    e21 = ema(close, 21).iloc[-1]
    r = rsi(close, 14).iloc[-1]
    ml = _ml_proba(df)

    s = 0.0
    if direction == 1:
        if e9 > e21:
            s += 0.3
        if r > 50:
            s += 0.2
        if close.iloc[-1] > e21:
            s += 0.2
        s += ml * 0.3                 # مساهمة متصلة (V2)
    else:
        if e9 < e21:
            s += 0.3
        if r < 50:
            s += 0.2
        if close.iloc[-1] < e21:
            s += 0.2
        s += (1.0 - ml) * 0.3         # انعكاس للبيع

    # عقوبة التقلب المرتفع (دون الفوضى)
    if vol_std > 0.04:
        s -= VOL_PENALTY

    return max(0.0, min(s, 1.0))


def passes_gate(df, direction, min_score=MIN_SCORE):
    """هل تجتاز الإشارة البوابة المؤسسية؟ تعيد (نجاح, الدرجة)."""
    s = institutional_score(df, direction)
    return s >= min_score, s
