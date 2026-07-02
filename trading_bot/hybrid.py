"""
[4] Hybrid AI Trading System — النظام الهجين (قواعد + ذكاء اصطناعي).

يدمج قوة نوعين من الذكاء:
  • القواعد (Rules): إشارات المؤشرات الكلاسيكية (سريعة، شفّافة).
  • الذكاء الاصطناعي (ML): نموذج Gradient Boosting يقدّر احتمال الصعود.

القرار الهجين: ندخل فقط عندما "تتفق" القاعدة مع النموذج — أي عندما
تؤكّد الإشارة الكلاسيكية ويوافقها احتمال النموذج فوق عتبة الثقة.
هذا يقلّل الإشارات الكاذبة عبر طلب تأكيد مزدوج.
"""
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from ml_features import build_features


class HybridAI:
    def __init__(self, prob_threshold=0.55):
        self.prob_threshold = prob_threshold
        self.model = None
        self.feature_names = None

    def train(self, df_train):
        """تدريب نموذج الـ ML على بيانات التدريب."""
        X, y, names, _ = build_features(df_train)
        if len(X) < 50 or y.nunique() < 2:
            return False
        self.feature_names = names
        self.model = GradientBoostingClassifier(
            n_estimators=120, max_depth=3, learning_rate=0.05,
            subsample=0.8, random_state=42)
        self.model.fit(X, y)
        return True

    def predict_proba_frame(self, df):
        """احتمال الصعود لكل صف (مفهرس مثل مخرجات build_features)."""
        X, y, names, meta = build_features(df)
        if self.model is None or len(X) == 0:
            return None, None
        proba = self.model.predict_proba(X[self.feature_names])[:, 1]
        return proba, meta

    def confirm(self, proba_value, rule_direction):
        """
        قرار هجين: يؤكّد إشارة القاعدة فقط إن وافقها النموذج.
        rule_direction: -1/0/1 من القواعد. proba_value: احتمال الصعود.
        """
        if rule_direction == 1 and proba_value >= self.prob_threshold:
            return 1
        if rule_direction == -1 and proba_value <= (1 - self.prob_threshold):
            return -1
        return 0
