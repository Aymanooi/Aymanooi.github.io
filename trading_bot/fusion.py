"""
[5] Signal Fusion Engine — محرّك دمج الإشارات.

يجمع إشارات من عدة مصادر مستقلة (اتجاه، زخم، سيولة، SMC) ويصوّت
بينها بأوزان. الفكرة: إشارة يؤكّدها عدة أنظمة مستقلة أقوى من إشارة
نظام واحد. يقلّل الضجيج ويرفع جودة القرار.
"""


class SignalFusionEngine:
    def __init__(self, weights=None, threshold=0.5):
        # وزن كل مصدر إشارة
        self.weights = weights or {
            "trend": 1.0,
            "momentum": 1.0,
            "liquidity": 0.8,
            "smc": 0.8,
        }
        self.threshold = threshold

    def fuse(self, signals: dict):
        """
        signals: قاموس {اسم المصدر: -1/0/1}.
        يعيد (direction, confidence): الاتجاه النهائي ودرجة الثقة [0..1].
        """
        total_w = sum(self.weights.get(k, 0) for k in signals)
        if total_w == 0:
            return 0, 0.0
        score = sum(self.weights.get(k, 0) * v for k, v in signals.items())
        norm = score / total_w   # بين -1 و 1

        if norm >= self.threshold:
            return 1, abs(norm)
        if norm <= -self.threshold:
            return -1, abs(norm)
        return 0, abs(norm)
