"""
نموذج التعلّم الآلي للتنبؤ باتجاه السوق.

المنهجية الصارمة (لتجنّب خداع النفس):
  1. تقسيم زمني صارم: تدريب على الماضي، اختبار على المستقبل (لا خلط عشوائي).
  2. مقارنة دقّة النموذج بخطّ الأساس (Baseline = توقّع الفئة الأغلب دائمًا).
     إن لم يتفوّق النموذج على هذا الخطّ بوضوح، فهو لا يتعلّم شيئًا مفيدًا.
  3. اختبار مالي حقيقي: نحوّل تنبؤات النموذج إلى صفقات على بيانات
     لم يرها، ونقيس العائد بعد الرسوم.

نستخدم Gradient Boosting (نموذج قوي للبيانات الجدولية).
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score

import config as cfg
from data_feed import fetch_history
from ml_features import build_features

TAKER_FEE = cfg.TAKER_FEE


def train_eval_symbol(symbol, total_candles, horizon=1, train_frac=0.7,
                      prob_threshold=0.55, verbose=True):
    """تدريب وتقييم النموذج على زوج واحد. يعيد قاموس النتائج."""
    raw = fetch_history(symbol, total=total_candles)
    X, y, names, meta = build_features(raw, horizon=horizon)

    # ---- تقسيم زمني صارم ----
    split = int(len(X) * train_frac)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    future_ret_test = meta["_future_ret"].iloc[split:].reset_index(drop=True)

    if len(X_test) < 30 or y_train.nunique() < 2:
        return None

    # ---- تدريب النموذج ----
    model = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.05,
        subsample=0.8, random_state=42,
    )
    model.fit(X_train, y_train)

    # ---- التقييم الإحصائي ----
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    acc = accuracy_score(y_test, pred)
    # خطّ الأساس: توقّع الفئة الأغلب في التدريب دائمًا
    majority = y_train.mode()[0]
    baseline_acc = (y_test == majority).mean()
    try:
        auc = roc_auc_score(y_test, proba)
    except ValueError:
        auc = float("nan")
    prec = precision_score(y_test, pred, zero_division=0)

    # ---- الاختبار المالي الحقيقي ----
    # ندخل صفقة شراء فقط عندما تكون ثقة النموذج عالية (proba >= prob_threshold)
    signals = proba >= prob_threshold
    # عائد كل صفقة = العائد المستقبلي الفعلي - رسوم الدخول والخروج
    trade_returns = future_ret_test[signals] - 2 * TAKER_FEE
    n_trades = int(signals.sum())
    if n_trades > 0:
        total_return = (1 + trade_returns).prod() - 1
        win_rate = (trade_returns > 0).mean() * 100
        avg_return = trade_returns.mean() * 100
    else:
        total_return = win_rate = avg_return = 0.0

    result = {
        "symbol": symbol, "samples_test": len(X_test),
        "accuracy": acc, "baseline": baseline_acc, "edge": acc - baseline_acc,
        "auc": auc, "precision": prec,
        "n_trades": n_trades, "total_return": total_return * 100,
        "win_rate": win_rate, "avg_return": avg_return,
        "model": model, "feature_names": names,
    }

    if verbose:
        print(f"  دقّة النموذج:      {acc*100:.1f}%  (خطّ الأساس: {baseline_acc*100:.1f}%)")
        edge = acc - baseline_acc
        flag = "✅" if edge > 0.02 else ("≈" if edge > -0.02 else "❌")
        print(f"  الميزة فوق الأساس: {edge*100:+.1f}%  {flag}")
        print(f"  AUC:               {auc:.3f}  (0.5 = تخمين عشوائي)")
        print(f"  صفقات عالية الثقة: {n_trades}")
        if n_trades > 0:
            print(f"  عائد الاختبار:     {total_return*100:+.2f}%  | نجاح {win_rate:.0f}%")

    return result


def feature_importance(result, top=8):
    """طباعة أهم الخصائص التي اعتمد عليها النموذج."""
    model = result["model"]
    names = result["feature_names"]
    imp = sorted(zip(names, model.feature_importances_), key=lambda x: -x[1])
    print("  أهم الخصائص:")
    for name, val in imp[:top]:
        print(f"    {name:18s} {val*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="نموذج تعلّم آلي للتنبؤ بالسوق")
    parser.add_argument("--candles", type=int, default=4000)
    parser.add_argument("--horizon", type=int, default=1, help="آفق التنبؤ (شموع)")
    parser.add_argument("--threshold", type=float, default=0.55,
                        help="عتبة ثقة الدخول")
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    parser.add_argument("--importance", action="store_true",
                        help="عرض أهم الخصائص")
    args = parser.parse_args()

    print("🤖 نموذج التعلّم الآلي — Gradient Boosting")
    print(f"   آفق التنبؤ: {args.horizon} شمعة | عتبة الثقة: {args.threshold}")
    print(f"   تقسيم زمني صارم: 70% تدريب / 30% اختبار\n")

    results = []
    for symbol in args.symbols:
        print(f"▶ {symbol}")
        try:
            r = train_eval_symbol(symbol, args.candles, args.horizon,
                                  prob_threshold=args.threshold)
        except Exception as e:
            print(f"  ✗ خطأ: {e}")
            continue
        if r is None:
            print("  ⚠️ بيانات غير كافية")
            continue
        if args.importance:
            feature_importance(r)
        results.append(r)
        print()

    if results:
        print("=" * 60)
        print("                  📊  الحكم النهائي")
        print("=" * 60)
        avg_acc = np.mean([r["accuracy"] for r in results])
        avg_base = np.mean([r["baseline"] for r in results])
        avg_edge = np.mean([r["edge"] for r in results])
        avg_auc = np.nanmean([r["auc"] for r in results])
        avg_ret = np.mean([r["total_return"] for r in results])
        winners = sum(1 for r in results if r["total_return"] > 0)
        print(f"  متوسط دقّة النموذج:        {avg_acc*100:.1f}%")
        print(f"  متوسط خطّ الأساس:          {avg_base*100:.1f}%")
        print(f"  متوسط الميزة الحقيقية:     {avg_edge*100:+.1f}%")
        print(f"  متوسط AUC:                 {avg_auc:.3f}")
        print(f"  متوسط عائد الاختبار:       {avg_ret:+.2f}%")
        print(f"  أزواج رابحة خارج العيّنة:  {winners}/{len(results)}")
        print("=" * 60)
        print("\n📌 التفسير:")
        if avg_edge > 0.03 and avg_auc > 0.55 and avg_ret > 0:
            print("   النموذج يُظهر ميزة تنبّؤية حقيقية — يستحق دراسة أعمق.")
        elif avg_auc < 0.53:
            print("   AUC قريب من 0.5 = النموذج لا يتنبّأ أفضل من العشوائية.")
            print("   هذا متوقّع علميًا: حركة السعر قصيرة المدى شبه عشوائية.")
        else:
            print("   ميزة ضعيفة/غير مستقرة — لا تكفي للتغلّب على الرسوم بثقة.")


if __name__ == "__main__":
    main()
