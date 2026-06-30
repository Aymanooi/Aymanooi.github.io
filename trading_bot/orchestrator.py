"""
[2] Meta Strategy Orchestrator — المنسّق الأعلى للاستراتيجيات.

العقل الذي يقرّر "أي استراتيجية تعمل الآن" حسب نظام السوق المكتشف:
  • TREND_UP / TREND_DOWN → نفعّل الاتجاه + الزخم (يعملان في الاتجاهات).
  • RANGE                 → نفعّل SMC + السيولة (انعكاسات في النطاق).
  • HIGH_VOL              → نتوقّف عن التداول (حماية).

يحوّل مجموعة استراتيجيات منفصلة إلى نظام واحد واعٍ بالسياق.
"""
from regime import TREND_UP, TREND_DOWN, RANGE, HIGH_VOL


class MetaOrchestrator:
    def __init__(self):
        # أي مصادر الإشارة نُفعّل في كل نظام
        self.regime_map = {
            TREND_UP:   {"trend", "momentum"},
            TREND_DOWN: {"trend", "momentum"},
            RANGE:      {"smc", "liquidity"},
            HIGH_VOL:   set(),   # لا تداول
        }

    def active_sources(self, regime):
        """مجموعة مصادر الإشارة المفعّلة في النظام الحالي."""
        return self.regime_map.get(regime, set())

    def filter_signals(self, regime, all_signals: dict):
        """إبقاء إشارات المصادر المفعّلة فقط لهذا النظام."""
        active = self.active_sources(regime)
        return {k: v for k, v in all_signals.items() if k in active}
