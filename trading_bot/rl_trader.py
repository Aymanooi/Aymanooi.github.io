"""
[10] Reinforcement Learning Trading System — نظام التداول بالتعلّم المعزّز.

عميل Q-Learning جدولي (tabular) يتعلّم سياسة تداول عبر التجربة والخطأ:
  • الحالة (State): تكميم (RSI، الزخم، قوة الاتجاه، هل يحمل صفقة).
  • الأفعال (Actions): {انتظار، شراء/احتفاظ}.
  • المكافأة (Reward): عائد الشمعة التالية عند الاحتفاظ (ناقص الرسوم).

يتعلّم على بيانات التدريب، ثم يُختبر على بيانات لم يرها (out-of-sample).
⚠️ RL في الأسواق صعب للغاية وعرضة للإفراط في التحسين — نختبره بصرامة.
"""
import argparse
import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import ema, rsi, adx


def _build_state_features(df):
    """خصائص الحالة المكمّمة."""
    close = df["close"]
    r = rsi(close, 14)
    mom = close.pct_change(5)
    a = adx(df, 14)
    feats = pd.DataFrame({
        "rsi_bucket": pd.cut(r, bins=[0, 30, 45, 55, 70, 100], labels=False),
        "mom_bucket": pd.cut(mom, bins=[-1, -0.02, -0.005, 0.005, 0.02, 1], labels=False),
        "adx_bucket": pd.cut(a, bins=[0, 20, 30, 100], labels=False),
        "fut_ret": close.shift(-1) / close - 1,
    })
    return feats


def _state_key(row, holding):
    return (int(row["rsi_bucket"]), int(row["mom_bucket"]),
            int(row["adx_bucket"]), int(holding))


def train_q(df, episodes=30, alpha=0.1, gamma=0.95, eps=0.1, fee=cfg.TAKER_FEE):
    """تدريب جدول Q. يعيد القاموس Q."""
    feats = _build_state_features(df).dropna().reset_index(drop=True)
    Q = {}
    rng = np.random.default_rng(42)

    for _ in range(episodes):
        holding = 0
        for i in range(len(feats) - 1):
            row = feats.iloc[i]
            s = _state_key(row, holding)
            Q.setdefault(s, [0.0, 0.0])
            # سياسة إبسلون-جشعة
            if rng.random() < eps:
                action = rng.integers(0, 2)
            else:
                action = int(np.argmax(Q[s]))
            # المكافأة: عائد الشمعة التالية إن كنا نحتفظ (action=1)
            ret = row["fut_ret"]
            if action == 1:
                reward = ret - (fee if holding == 0 else 0)  # رسوم عند فتح صفقة
                next_holding = 1
            else:
                reward = -(fee if holding == 1 else 0)        # رسوم عند الإغلاق
                next_holding = 0
            ns = _state_key(feats.iloc[i + 1], next_holding)
            Q.setdefault(ns, [0.0, 0.0])
            Q[s][action] += alpha * (reward + gamma * max(Q[ns]) - Q[s][action])
            holding = next_holding
    return Q


def evaluate_q(df, Q, fee=cfg.TAKER_FEE):
    """تقييم السياسة المتعلّمة على بيانات الاختبار. يعيد العائد التراكمي وعدد الصفقات."""
    feats = _build_state_features(df).dropna().reset_index(drop=True)
    capital = 1.0
    holding = 0
    trades = 0
    for i in range(len(feats) - 1):
        s = _state_key(feats.iloc[i], holding)
        action = int(np.argmax(Q[s])) if s in Q else 0
        ret = feats.iloc[i]["fut_ret"]
        if action == 1:
            if holding == 0:
                capital *= (1 - fee)  # رسوم فتح
                trades += 1
            capital *= (1 + ret)
            holding = 1
        else:
            if holding == 1:
                capital *= (1 - fee)  # رسوم إغلاق
            holding = 0
    return (capital - 1) * 100, trades


def main():
    parser = argparse.ArgumentParser(description="نظام التداول بالتعلّم المعزّز")
    parser.add_argument("--candles", type=int, default=4000)
    parser.add_argument("--symbols", nargs="*", default=cfg.SYMBOLS)
    args = parser.parse_args()

    print("🎮 نظام التعلّم المعزّز (Q-Learning)")
    print("   تدريب على 70% / اختبار على 30% (out-of-sample)\n")

    results = []
    for symbol in args.symbols:
        df = fetch_history(symbol, total=args.candles)
        split = int(len(df) * 0.7)
        train_df = df.iloc[:split].reset_index(drop=True)
        test_df = df.iloc[split:].reset_index(drop=True)
        Q = train_q(train_df)
        train_ret, _ = evaluate_q(train_df, Q)
        test_ret, n = evaluate_q(test_df, Q)
        results.append(test_ret)
        print(f"  {symbol}: تدريب {train_ret:+.1f}% | اختبار {test_ret:+.1f}% ({n} صفقة)")

    print(f"\n  متوسط عائد الاختبار: {np.mean(results):+.2f}%")
    print(f"  أزواج رابحة: {sum(1 for r in results if r > 0)}/{len(results)}")


if __name__ == "__main__":
    main()
