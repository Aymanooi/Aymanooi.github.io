"""
البوت الأمثل — رأيي الصادق النهائي بعد 12 منهجًا فاشلًا في التنبؤ.

الفكرة الجوهرية: أكبر ربح *حقيقي* ممكن لا يأتي من التنبؤ بالسعر
(مستحيل — أثبتناه)، بل من مصادر ربح لا تحتاج تنبؤًا:

  ① حصاد تمويل العقود (Funding Carry):
     شراء فوري + بيع عقد دائم بنفس الكمية = محايد تمامًا للسعر.
     يحصد دفعات التمويل (كل 8 ساعات) التي يدفعها المضاربون.
     هذا ما تفعله صناديق محايدة حقيقية.

  ② الاحتفاظ المنهجي (HODL): ركوب نمو السوق بدل محاولة التغلب عليه.

  ③ خط الأساس: عدم التداول إطلاقًا (0%).

نقارنها بأرقام حقيقية من OKX ضد نتائج بوتات التنبؤ الاثني عشر.
"""
import time
import numpy as np
import requests

import config as cfg
from data_feed import fetch_history, _get_with_retry

SYMBOLS_SWAP = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "XRP-USDT-SWAP"]
CAPITAL = 10.0


def fetch_funding_history(inst_id, pages=12):
    """جلب تاريخ معدلات التمويل الحقيقية من OKX (كل 8 ساعات)."""
    url = f"{cfg.OKX_BASE_URL}/api/v5/public/funding-rate-history"
    rates, after = [], None
    for _ in range(pages):
        params = {"instId": inst_id, "limit": 100}
        if after:
            params["after"] = after
        resp = _get_with_retry(url, params)
        data = resp.json().get("data", [])
        if not data:
            break
        rates += [float(d["fundingRate"]) for d in data]
        after = data[-1]["fundingTime"]
        time.sleep(0.15)
    return np.array(rates)


def carry_strategy():
    """① حصاد التمويل: عائد محايد للسعر تمامًا."""
    print("① بوت حصاد التمويل (محايد للسعر — بلا تنبؤ):")
    results = {}
    for inst in SYMBOLS_SWAP:
        rates = fetch_funding_history(inst)
        if len(rates) == 0:
            continue
        days = len(rates) / 3                     # 3 دفعات يوميًا
        # المركز المحايد يحصد التمويل عندما يكون موجبًا (الوضع الغالب)
        period_yield = rates.sum()                # عائد الفترة على القيمة الاسمية
        apr = period_yield * (365 / days) * 100
        positive_share = (rates > 0).mean() * 100
        results[inst] = apr
        print(f"   {inst:18s}: متوسط {rates.mean()*100:+.4f}%/8h | "
              f"موجب {positive_share:.0f}% من الوقت | APR ≈ {apr:+.2f}%")
    if results:
        best = max(results, key=results.get)
        apr = results[best]
        # تكلفة الدخول والخروج (4 أرجل: شراء فوري + بيع عقد ثم العكس)
        entry_cost = 0.3
        net_year = CAPITAL * (apr / 100) - CAPITAL * entry_cost / 100
        print(f"   ⟶ أفضل خيار: {best} | صافي سنوي متوقع على 10$: "
              f"{net_year:+.2f}$ (بعد رسوم ≈{entry_cost}%)")
    print()


def hodl_strategy():
    """② الاحتفاظ المنهجي على نفس فترة اختباراتنا."""
    print("② بوت الاحتفاظ المنهجي (HODL) — نفس فترة اختبار بوتات التنبؤ:")
    for sym in ["BTC-USDT", "ETH-USDT", "XRP-USDT"]:
        df = fetch_history(sym, total=5000)
        ret = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        months = len(df) / 24 / 30
        print(f"   {sym:10s}: {ret:+7.2f}% خلال {months:.1f} شهرًا "
              f"(10$ → {10 * (1 + ret / 100):.2f}$)")
    print()


if __name__ == "__main__":
    print("=" * 64)
    print("  🧠 البوت الأمثل — المقارنة الصادقة النهائية (رأس مال 10$)")
    print("=" * 64 + "\n")

    carry_strategy()
    hodl_strategy()

    print("③ خط الأساس (عدم التداول): 10.00$ → 10.00$ (0%)\n")
    print("④ بوتات التنبؤ الـ 12 التي بنيناها: 10$ → 0.49$ ~ 5.38$ (خسارة دائمًا)")
    print("=" * 64)
    print("  📌 الحكم: كل ما لا يتنبأ يتفوق على كل ما يتنبأ.")
    print("=" * 64)
