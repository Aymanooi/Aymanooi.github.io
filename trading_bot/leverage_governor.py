"""
⚖️ حاكم الرافعة — Adaptive Leverage Controller

يجيب على السؤال الذي لا يسأله المقامرون: "ما أقصى رافعة تنجو من البيانات؟"

السياق: رفع رافعة حصاد التمويل إلى L يضاعف العائد ×L، لكن ساق العقد
القصير تُصفّى إذا ارتفع السعر بنسبة ≈ (1/L − هامش صيانة 2%).
  L=2  → التصفية عند ارتفاع ~48%
  L=5  → التصفية عند ارتفاع ~18%
  L=10 → التصفية عند ارتفاع ~8%

المنهج: لكل نقطة دخول تاريخية، نفحص هل ارتفع السعر فوق عتبة التصفية
خلال 30 يومًا. نحسب احتمال النجاة، ثم العائد الصافي المتوقع:
  APR(L) = L × APR_تمويل × P(نجاة) − تكلفة_تصفية × P(تصفية)
حيث تكلفة التصفية ≈ 6% من رأس المال (غرامة + رسوم + إعادة تموضع).
"""
import numpy as np

import config as cfg
from data_feed import fetch_history

BASE_FUNDING_APR = 0.02      # المثبت من best_bot.py
MAINT_MARGIN = 0.02          # هامش الصيانة التقريبي
LIQ_COST = 0.06              # كلفة حدث التصفية (نسبة من رأس المال)
HORIZON = 720                # 30 يومًا بشموع الساعة
SYMBOLS = ["BTC-USDT", "ETH-USDT", "XRP-USDT"]


def survival_analysis(closes, highs, liq_move):
    """نسبة نقاط الدخول التي نجت 30 يومًا دون بلوغ عتبة التصفية."""
    n = len(closes)
    liquidated = 0
    total = 0
    for i in range(0, n - HORIZON, 24):          # عيّنة دخول كل يوم
        entry = closes[i]
        window_max = highs[i + 1:i + HORIZON].max()
        total += 1
        if (window_max / entry - 1) >= liq_move:
            liquidated += 1
    return 1 - liquidated / total if total else 0.0, total


def main():
    print("=" * 66)
    print("  ⚖️ حاكم الرافعة — أقصى رافعة تتحمّلها البيانات (حصاد التمويل)")
    print("=" * 66)

    data = {}
    for s in SYMBOLS:
        df = fetch_history(s, total=5000)
        data[s] = (df["close"].values, df["high"].values)
        print(f"  ✓ {s}: {len(df)} شمعة")

    print(f"\n{'الرافعة':<9}{'عتبة التصفية':<14}{'P(نجاة 30ي)':<14}"
          f"{'APR صافٍ متوقع':<16}{'الحكم'}")
    print("-" * 66)

    best = (1, BASE_FUNDING_APR)
    for L in [1, 2, 3, 5, 7, 10]:
        liq_move = max(1 / L - MAINT_MARGIN, 0.005)
        survs = []
        for s, (c, h) in data.items():
            p, _ = survival_analysis(c, h, liq_move)
            survs.append(p)
        p_surv = float(np.mean(survs))
        # عدد أحداث التصفية المتوقعة سنويًا ≈ 12 نافذة شهرية × احتمال التصفية
        liq_per_year = 12 * (1 - p_surv)
        apr = L * BASE_FUNDING_APR * p_surv - LIQ_COST * liq_per_year
        if apr > best[1]:
            best = (L, apr)
        verdict = ("🟢 آمنة" if p_surv > 0.95 else
                   "🟡 هشّة" if p_surv > 0.80 else "🔴 انتحارية")
        print(f"  {L}x{'':<6}+{liq_move*100:>5.1f}%       {p_surv*100:>5.1f}%"
              f"        {apr*100:>+6.2f}%         {verdict}")

    print("=" * 66)
    L, apr = best
    print(f"  🏛️ قرار الحاكم: الرافعة المثلى المدعومة بالبيانات = {L}x")
    print(f"     العائد الصافي المتوقع عندها: {apr*100:+.2f}% سنويًا")
    print(f"     على 10$: {10*apr:+.2f}$ في السنة")
    print("=" * 66)
    print("\n  ⚠️ تحذير النظام (Regime Warning): بياناتنا من سوق هابطة —")
    print("     الارتفاعات الحادة نادرة فيها. في سوق صاعدة (قفزات 20-40%")
    print("     شهريًا كما في 2024) تنهار احتمالات النجاة للرافعات العالية.")
    print("     الحاكم يعيد الحساب على أحدث بيانات في كل تشغيل.")


if __name__ == "__main__":
    main()
