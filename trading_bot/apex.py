"""
⚡ APEX — الحارس الأعظم ⚡
أندر بوت تداول في العالم: الوحيد الذي يرفض التداول بلا برهان إحصائي.

الفكرة التي لا يملكها أي بوت تجاري:
  كل بوتات العالم *تفترض* أن استراتيجيتها تملك ميزة ثم تتداول.
  APEX يعكس المعادلة: يخضع كل استراتيجياته لاختبار دلالة إحصائية
  (Bootstrap) على أحدث البيانات، ولا يأذن بالتداول إلا لاستراتيجية
  أثبتت ميزة موجبة *ذات دلالة* بعد الرسوم (p < 0.05، عيّنة ≥ 30 صفقة).

  إن لم يثبت شيء → القرار السيادي: "حفظ رأس المال" + توجيه لحصاد
  التمويل (المصدر الموجب الوحيد المثبت، بلا تنبؤ).

قوّته الحقيقية: لا يمكن خداعه — لا بنافذة محظوظة، ولا بنسبة نجاح
مختلقة، ولا بحماس صاحبه. الميزة تُثبَت أو لا تداول.

بروتوكول القرار:
  ① جمع صفقات كل عائلة إشارات على نافذة حديثة متدحرجة (خارج أي ضبط)
  ② Bootstrap (5000 إعادة معاينة) لتوقّع الربح بعد الرسوم
  ③ البوابة: توقّع موجب + p < 0.05 + عيّنة كافية
  ④ المصرَّح لها فقط تتداول — تحت دروع بوت القلعة كاملةً
"""
import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from strategy_lab import (prepare, sig_donchian, sig_supertrend, sig_ichimoku,
                          sig_squeeze, sig_meanrev, sig_vwap, sig_momentum)
from uploaded_bots import sig_advanced_vote

FEE = cfg.TAKER_FEE
WINDOW = 1500          # نافذة التقييم الحديثة (شموع)
MIN_TRADES = 30        # أقل عيّنة مقبولة إحصائيًا
P_THRESHOLD = 0.05     # عتبة الدلالة
N_BOOT = 5000          # إعادات المعاينة

FAMILIES = {
    "Momentum Confluence": sig_momentum,
    "Donchian Breakout":   sig_donchian,
    "Supertrend":          sig_supertrend,
    "Ichimoku":            sig_ichimoku,
    "Bollinger Squeeze":   sig_squeeze,
    "Mean Reversion":      sig_meanrev,
    "VWAP Reversion":      sig_vwap,
    "Advanced Vote (مرفوع)": sig_advanced_vote,
}


def collect_trades(df, sig_func):
    """جمع عوائد الصفقات المنفردة (نسبة من رأس المال) — لا مجاميع تُخفي التفاصيل."""
    pnls = []
    pos = None
    for i in range(1, len(df)):
        r = df.iloc[i]
        if pos is not None:
            d = pos["d"]
            hit = None
            if d == 1:
                if r["low"] <= pos["sl"]:
                    hit = pos["sl"]
                elif r["high"] >= pos["tp"]:
                    hit = pos["tp"]
            else:
                if r["high"] >= pos["sl"]:
                    hit = pos["sl"]
                elif r["low"] <= pos["tp"]:
                    hit = pos["tp"]
            if hit is not None:
                gross = (hit - pos["e"]) / pos["e"] * d
                fees = FEE * 2
                pnls.append(gross - fees)   # عائد الصفقة على قيمتها الاسمية
                pos = None
        if pos is None and not pd.isna(r["atr"]) and r["atr"] > 0:
            d = sig_func(df, i)
            if d != 0:
                e = r["close"]
                risk = r["atr"] * 1.5
                pos = {"d": d, "e": e, "sl": e - risk * d, "tp": e + risk * 2 * d}
    return pnls


def bootstrap_p(pnls, n_boot=N_BOOT, seed=42):
    """احتمال أن يكون التوقّع الحقيقي ≤ صفر (p-value بالمعاينة المعادة)."""
    arr = np.array(pnls)
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(arr, size=len(arr), replace=True).mean()
                      for _ in range(n_boot)])
    return float((means <= 0).mean())


def main():
    print("=" * 68)
    print("  ⚡ APEX — الحارس الأعظم | بروتوكول الإذن بالتداول")
    print(f"  البوابة: توقّع موجب بعد الرسوم + p < {P_THRESHOLD} + عيّنة ≥ {MIN_TRADES}")
    print("=" * 68)

    print("\nجلب أحدث البيانات...")
    data = {}
    for s in cfg.SYMBOLS:
        data[s] = prepare(fetch_history(s, total=WINDOW))
    print(f"  ✓ {len(data)} أزواج × {WINDOW} شمعة (النافذة الحديثة)\n")

    # تصحيح Bonferroni للاختبار المتعدد: نختبر 8 عائلات، فاحتمال نجاح
    # واحدة بالصدفة عند 0.05 يبلغ ~34%. العتبة المصحّحة = 0.05 / 8.
    corrected_p = P_THRESHOLD / len(FAMILIES)
    print(f"  تصحيح الاختبار المتعدد (Bonferroni): p < {corrected_p:.5f}")
    print(f"\n{'العائلة':<24}{'صفقات':<8}{'التوقّع/صفقة':<14}{'p-value':<10}{'الحكم'}")
    print("-" * 68)

    authorized = []
    for name, fn in FAMILIES.items():
        pnls = []
        for s, df in data.items():
            pnls += collect_trades(df, fn)
        n = len(pnls)
        if n < MIN_TRADES:
            print(f"{name:<24}{n:<8}{'—':<14}{'—':<10}⚪ عيّنة غير كافية")
            continue
        expectancy = np.mean(pnls) * 100
        p = bootstrap_p(pnls)
        passed = expectancy > 0 and p < corrected_p
        near = expectancy > 0 and p < P_THRESHOLD
        verdict = "🟢 مُصرَّح" if passed else ("🟡 واعد لكن دون العتبة المصحّحة" if near else "🔴 مرفوض")
        print(f"{name:<24}{n:<8}{expectancy:+.3f}%{'':<7}{p:.3f}     {verdict}")
        if passed:
            authorized.append((name, expectancy, p))

    print("=" * 68)
    if authorized:
        print("  🟢 القرار السيادي: الإذن بالتداول للعائلات المُصرَّح لها")
        for name, e, p in authorized:
            print(f"     → {name} (توقّع {e:+.3f}%/صفقة، p={p:.3f})")
        print("     التنفيذ حصريًا تحت دروع بوت القلعة (fortress.py)")
    else:
        print("  🛡️ القرار السيادي: لا ميزة مُثبتة إحصائيًا في السوق الحالي")
        print("     → التداول الاتجاهي: محظور (حفظ رأس المال)")
        print("     → التخصيص الموصى به: حصاد التمويل (best_bot.py)")
        print("       المصدر الموجب الوحيد المثبت — بلا تنبؤ (+2% سنويًا)")
    print("=" * 68)
    print("\n  «أقوى بوت ليس الذي يتداول أكثر — بل الذي يعرف متى يمتنع.»")


if __name__ == "__main__":
    main()
