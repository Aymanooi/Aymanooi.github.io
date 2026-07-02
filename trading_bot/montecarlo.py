"""
[Monte Carlo Risk Engine] — محرّك مخاطر مونت كارلو.

يجيب على سؤال: "ماذا يحدث لو دخلتُ برأس المال كامل (All-in)؟"

يحاكي آلاف المسارات المحتملة باستخدام إحصاءات صفقاتنا الحقيقية
(من الاختبارات السابقة)، ويقارن ثلاثة أساليب:
  • مخاطرة ثابتة 2% (آمن)
  • رأس المال كامل بلا رافعة
  • رأس المال كامل برافعة 10x (وضعك في OKX Futures)

يقيس: متوسط النتيجة، الوسيط، واحتمال الإفلاس (Risk of Ruin).
"""
import numpy as np

# إحصاءات حقيقية من اختباراتنا: نسبة نجاح ~38%، نسبة عائد/مخاطرة 1:2
WIN_RATE = 0.38
RR = 2.0
STOP_PCT = 0.04      # وقف الخسارة ~4% من سعر الدخول (نموذجي للساعة)
FEE = 0.001          # رسوم ذهابًا وإيابًا
N_TRADES = 100       # عدد الصفقات في المسار
N_PATHS = 20000      # عدد المسارات المحاكاة
RUIN_LEVEL = 0.10    # نعتبر الحساب "مفلسًا" إذا هبط تحت 10% من البداية


def simulate(mode, leverage=1.0, risk_frac=0.02, rng=None):
    """محاكاة مسار واحد. يعيد رأس المال النهائي (كنسبة من البداية)."""
    rng = rng or np.random.default_rng()
    capital = 1.0
    for _ in range(N_TRADES):
        if capital <= 0:
            return 0.0
        win = rng.random() < WIN_RATE
        # حركة السعر لصالحنا/ضدنا
        move = STOP_PCT * RR if win else -STOP_PCT

        if mode == "full":
            # كامل رأس المال كقيمة اسمية × الرافعة
            pnl_frac = move * leverage - FEE * leverage
            capital *= (1 + pnl_frac)
            if capital <= 0:           # تصفية كاملة
                return 0.0
        else:  # مخاطرة ثابتة
            risk_amount = capital * risk_frac
            pnl = (risk_amount * RR if win else -risk_amount) - capital * FEE * 0.1
            capital += pnl
    return max(0.0, capital)


def run_mode(name, **kwargs):
    rng = np.random.default_rng(42)
    finals = np.array([simulate(rng=rng, **kwargs) for _ in range(N_PATHS)])
    ruined = np.mean(finals < RUIN_LEVEL) * 100
    median = np.median(finals)
    mean = np.mean(finals)
    p95 = np.percentile(finals, 95)
    print(f"\n  {name}")
    print(f"    الوسيط (الأكثر واقعية): {median*100:6.1f}% من رأس المال")
    print(f"    المتوسط:                {mean*100:6.1f}%")
    print(f"    أفضل 5% (حظ نادر):       {p95*100:6.1f}%")
    print(f"    احتمال الإفلاس:          {ruined:5.1f}%")


if __name__ == "__main__":
    print("=" * 60)
    print("   🎲 محاكاة مونت كارلو: ماذا لو دخلت برأس المال كامل؟")
    print("=" * 60)
    print(f"   {N_PATHS:,} مسار محاكى × {N_TRADES} صفقة")
    print(f"   إحصاءات حقيقية: نجاح {WIN_RATE*100:.0f}%، عائد/مخاطرة 1:{RR:.0f}")

    run_mode("① مخاطرة ثابتة 2% (الأسلوب الآمن)", mode="risk", risk_frac=0.02)
    run_mode("② رأس المال كامل — بلا رافعة", mode="full", leverage=1.0)
    run_mode("③ رأس المال كامل — رافعة 10x (وضع OKX Futures)", mode="full", leverage=10.0)

    print("\n" + "=" * 60)
    print("   📌 الخلاصة: حجم الرهان لا يصنع ميزة — بل يضخّم المصير.")
    print("=" * 60)
