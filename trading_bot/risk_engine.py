"""
[3] Dynamic Risk Engine — محرّك المخاطر الديناميكي.

بدلًا من مخاطرة ثابتة، يعدّل حجم المخاطرة حسب الظروف:
  • استهداف التقلّب (Volatility Targeting): مخاطرة أقل عند التقلّب العالي.
  • سلسلة النتائج (Streak): تقليل المخاطرة بعد خسائر متتالية (حماية رأس المال).
  • النظام (Regime): مخاطرة أقل في أنظمة السوق الخطرة.

الهدف: البقاء في اللعبة. الناجي هو من يحمي رأس ماله في الفترات السيئة.
"""


class DynamicRiskEngine:
    def __init__(self, base_risk=0.02, min_risk=0.005, max_risk=0.03,
                 target_vol=0.02):
        self.base_risk = base_risk
        self.min_risk = min_risk
        self.max_risk = max_risk
        self.target_vol = target_vol
        self.loss_streak = 0
        self.win_streak = 0

    def update(self, pnl):
        """تحديث سلسلة النتائج بعد إغلاق صفقة."""
        if pnl > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0

    def risk_fraction(self, atr_pct=None, regime=None):
        """حساب نسبة المخاطرة الحالية من رأس المال."""
        risk = self.base_risk

        # 1) استهداف التقلّب: نسبة معكوسة مع التقلّب الحالي
        if atr_pct and atr_pct > 0:
            risk *= min(2.0, self.target_vol / atr_pct)

        # 2) تقليص بعد خسائر متتالية (نخفّض النصف بعد كل خسارتين)
        if self.loss_streak >= 2:
            risk *= 0.5 ** (self.loss_streak // 2)

        # 3) أنظمة السوق الخطرة
        if regime == "HIGH_VOL":
            risk *= 0.4

        return max(self.min_risk, min(self.max_risk, risk))
