"""
النظام المتقدّم الموحّد — يدمج كل المكوّنات العشرة في خطّ قرار واحد.

تدفّق القرار لكل شمعة:
  1) كشف نظام السوق        [Market Regime Detection]
  2) فلتر التقلّب          [Volatility Filter]  → تجاهل البيئات الخطرة
  3) توليد إشارات متعددة:  اتجاه + زخم متعدد العوامل + سيولة + SMC
  4) المنسّق يختار المصادر المناسبة للنظام  [Meta Orchestrator]
  5) دمج الإشارات بالتصويت  [Signal Fusion Engine]
  6) تأكيد الذكاء الاصطناعي [Hybrid AI]  → تأكيد مزدوج
  7) محرّك المخاطر يحدّد الحجم [Dynamic Risk Engine]

يُقيّم بصرامة عبر تقسيم تدريب/اختبار (out-of-sample).
"""
import argparse
import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from regime import detect_regime, HIGH_VOL
from vol_filter import volatility_ok
from momentum import add_momentum, momentum_signal
from liquidity import add_liquidity, liquidity_signal
from smc import add_smc, entry_signal_smc
from strategy import _entry_signal_trend, compute_stops
from fusion import SignalFusionEngine
from orchestrator import MetaOrchestrator
from risk_engine import DynamicRiskEngine
from hybrid import HybridAI


def prepare_all(raw):
    """إضافة كل الأعمدة التي تحتاجها المكوّنات."""
    df = add_indicators(raw, cfg)
    df = detect_regime(df)
    df = add_momentum(df)
    df = add_liquidity(df)
    df = add_smc(df, cfg)
    return df


def collect_signals(df, i):
    """جمع إشارات كل المصادر عند الفهرس i."""
    return {
        "trend": _entry_signal_trend(df, i, cfg),
        "momentum": momentum_signal(df, i),
        "liquidity": liquidity_signal(df, i),
        "smc": entry_signal_smc(df, i, cfg),
    }


def run(symbol, total_candles, use_ai=True, train_ratio=0.7, verbose=False):
    """تشغيل النظام الكامل على زوج. يعيد نتائج الاختبار خارج العيّنة."""
    raw = fetch_history(symbol, total=total_candles)
    df = prepare_all(raw)

    split = int(len(df) * train_ratio)

    # تدريب الذكاء الاصطناعي على جزء التدريب فقط
    ai = None
    if use_ai:
        ai = HybridAI(prob_threshold=0.53)
        if not ai.train(raw.iloc[:split]):
            ai = None
        else:
            proba, meta = ai.predict_proba_frame(raw)
            # ربط الاحتمالات بالطوابع الزمنية
            ai_proba = pd.Series(proba, index=meta["_ts"].values) if proba is not None else None

    fusion = SignalFusionEngine(threshold=0.5)
    orch = MetaOrchestrator()
    risk = DynamicRiskEngine(base_risk=cfg.RISK_PER_TRADE)

    capital = cfg.INITIAL_CAPITAL
    position = None
    pnls = []

    # نبدأ من جزء الاختبار فقط (out-of-sample)
    for i in range(split, len(df)):
        row = df.iloc[i]

        # إدارة صفقة مفتوحة
        if position is not None:
            exit_price = None
            d = position["direction"]
            if d == 1:
                if row["low"] <= position["sl"]:
                    exit_price = position["sl"]
                elif row["high"] >= position["tp"]:
                    exit_price = position["tp"]
            else:
                if row["high"] >= position["sl"]:
                    exit_price = position["sl"]
                elif row["low"] <= position["tp"]:
                    exit_price = position["tp"]
            if exit_price is not None:
                gross = (exit_price - position["entry"]) * position["qty"] * d
                fees = (position["entry"] + exit_price) * position["qty"] * cfg.TAKER_FEE
                pnl = gross - fees
                capital += pnl
                pnls.append(pnl)
                risk.update(pnl)
                position = None

        if position is not None:
            continue

        # 1-2) فلتر النظام والتقلّب
        if row["regime"] == HIGH_VOL or not volatility_ok(df, i):
            continue

        # 3-4) جمع الإشارات وتصفيتها بالمنسّق
        signals = collect_signals(df, i)
        active = orch.filter_signals(row["regime"], signals)
        if not active:
            continue

        # 5) دمج الإشارات
        direction, conf = fusion.fuse(active)
        if direction == 0:
            continue

        # 6) تأكيد الذكاء الاصطناعي
        if ai is not None and ai_proba is not None:
            ts = row["ts"]
            if ts in ai_proba.index:
                p = float(ai_proba.loc[ts]) if np.ndim(ai_proba.loc[ts]) == 0 else float(ai_proba.loc[ts].iloc[0])
                if ai.confirm(p, direction) == 0:
                    continue

        # 7) حجم الصفقة من محرّك المخاطر الديناميكي
        if pd.isna(row["atr"]) or row["atr"] <= 0:
            continue
        rf = risk.risk_fraction(atr_pct=row.get("atr_pct"), regime=row["regime"])
        entry = row["close"]
        sl, tp = compute_stops(entry, row["atr"], direction, cfg)
        risk_per_unit = abs(entry - sl)
        if risk_per_unit <= 0:
            continue
        qty = (capital * rf) / risk_per_unit
        if qty <= 0 or entry * qty / cfg.MAX_LEVERAGE > capital:
            continue
        position = {"direction": direction, "entry": entry, "sl": sl, "tp": tp, "qty": qty}
        if verbose:
            tag = "L" if direction == 1 else "S"
            print(f"  [{symbol}/{tag}] {row['regime']} conf={conf:.2f} rf={rf:.3f}")

    ret = (capital - cfg.INITIAL_CAPITAL) / cfg.INITIAL_CAPITAL * 100
    wins = sum(1 for p in pnls if p > 0)
    return {"symbol": symbol, "return": ret, "trades": len(pnls),
            "win_rate": (wins / len(pnls) * 100) if pnls else 0}


def main():
    parser = argparse.ArgumentParser(description="النظام المتقدّم الموحّد")
    parser.add_argument("--candles", type=int, default=4000)
    parser.add_argument("--no-ai", action="store_true", help="تعطيل تأكيد الذكاء الاصطناعي")
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("   🚀 النظام المتقدّم الموحّد (10 مكوّنات)")
    print("=" * 60)
    print("   Regime · VolFilter · Momentum · Liquidity · SMC")
    print("   Orchestrator · Fusion · HybridAI · DynamicRisk")
    print(f"   التقييم: خارج العيّنة (30% أخيرة) | AI={'OFF' if args.no_ai else 'ON'}\n")

    results = []
    for symbol in args.symbols:
        try:
            r = run(symbol, args.candles, use_ai=not args.no_ai, verbose=args.verbose)
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")
            continue
        results.append(r)
        print(f"  {symbol}: عائد {r['return']:+.2f}% | {r['trades']} صفقة | نجاح {r['win_rate']:.0f}%")

    if results:
        avg = np.mean([r["return"] for r in results])
        winners = sum(1 for r in results if r["return"] > 0)
        print("\n" + "=" * 60)
        print(f"  المتوسط الكلي خارج العيّنة: {avg:+.2f}%")
        print(f"  أزواج رابحة: {winners}/{len(results)}")
        print("=" * 60)


if __name__ == "__main__":
    main()
