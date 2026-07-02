"""
محاكاة محفظة متزامنة — المواصفات المطلوبة:
  • رأس المال: 10$
  • بدون BTC/ETH/SOL — عملات بديلة فقط
  • 4 صفقات متزامنة كحد أقصى، كل واحدة بـ 25% من رأس المال
  • رافعة 20x (الأقصى الواقعي للعملات البديلة في OKX)
  • إعادة دخول فورية في أول فرصة بعد الخروج
  • وقف 2% / هدف 4% (حركة سعر) — مضروبة في الرافعة على الهامش

⚠️ أموال وهمية (Paper) — لأمانك.
"""
import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from indicators import add_indicators
from strategy import entry_signal

START = 10.0
SIZE = 0.25          # 25% من رأس المال لكل صفقة
LEV = 20.0           # الرافعة القصوى الواقعية للبدائل
SL_PCT = 0.02        # وقف خسارة: حركة سعر 2%
TP_PCT = 0.04        # جني ربح: حركة سعر 4%
MAX_POS = 4          # 4 عملات في نفس الوقت
FEE = cfg.TAKER_FEE
RUIN = 0.5           # تحت 0.5$ لا يمكن فتح صفقة مجدية

# عملات بديلة (بدون BTC/ETH/SOL)
ALTS = ["XRP-USDT", "BNB-USDT", "DOGE-USDT", "ADA-USDT", "AVAX-USDT", "LINK-USDT"]


def load_all(candles=5000):
    """جلب وتجهيز كل العملات، ثم توحيد الخط الزمني."""
    data = {}
    for s in ALTS:
        try:
            df = add_indicators(fetch_history(s, total=candles), cfg)
            data[s] = df.set_index("ts")
            print(f"  ✓ {s}: {len(df)} شمعة")
        except Exception as e:
            print(f"  ✗ {s}: {e}")
    # الخط الزمني الموحّد = تقاطع الطوابع المشتركة
    common = None
    for df in data.values():
        common = df.index if common is None else common.intersection(df.index)
    common = common.sort_values()
    return data, common


def run():
    print("جلب البيانات...")
    data, timeline = load_all()
    print(f"\nخط زمني موحّد: {len(timeline)} شمعة ({timeline[0]} → {timeline[-1]})\n")

    # فهرسة موضعية سريعة لكل عملة
    pos_idx = {s: {ts: i for i, ts in enumerate(df.index)} for s, df in data.items()}
    dfs_reset = {s: df.reset_index() for s, df in data.items()}

    capital = START
    positions = {}          # symbol -> dict
    trades = wins = 0
    peak = START
    history = [(timeline[0], START)]

    for ts in timeline:
        # ---- إدارة الصفقات المفتوحة ----
        for s in list(positions.keys()):
            df = data[s]
            if ts not in df.index:
                continue
            row = df.loc[ts]
            p = positions[s]
            d, e = p["dir"], p["entry"]
            hit = None
            liq = 1.0 / LEV  # حركة 5% عكسية = تصفية الهامش
            if d == 1:
                if row["low"] <= e * (1 - min(SL_PCT, liq)):
                    hit = -min(SL_PCT, liq)
                elif row["high"] >= e * (1 + TP_PCT):
                    hit = TP_PCT
            else:
                if row["high"] >= e * (1 + min(SL_PCT, liq)):
                    hit = -min(SL_PCT, liq)
                elif row["low"] <= e * (1 - TP_PCT):
                    hit = TP_PCT
            if hit is not None:
                margin = p["margin"]
                pnl = margin * (hit * LEV) - margin * LEV * FEE * 2
                capital = max(0.0, capital + pnl)
                trades += 1
                if hit > 0:
                    wins += 1
                del positions[s]

        peak = max(peak, capital)
        history.append((ts, capital))
        if capital < RUIN:
            return capital, trades, wins, peak, history, "💥 إفلاس"

        # ---- فتح صفقات جديدة (إعادة دخول فورية) ----
        if len(positions) < MAX_POS:
            for s in ALTS:
                if s in positions or len(positions) >= MAX_POS:
                    continue
                if ts not in pos_idx[s]:
                    continue
                i = pos_idx[s][ts]
                if i < 1:
                    continue
                d = entry_signal(dfs_reset[s], i, cfg)
                if d != 0:
                    margin = capital * SIZE
                    if margin < 0.1:
                        continue
                    row = data[s].loc[ts]
                    positions[s] = {"dir": d, "entry": row["close"], "margin": margin}

    return capital, trades, wins, peak, history, "انتهت البيانات"


if __name__ == "__main__":
    cfg.STRATEGY = "smc"   # الأكثر نشاطًا — دخول شبه مستمر كما طُلب
    print("=" * 62)
    print("  📟 محفظة متزامنة: 10$ | 4 عملات × 25% | رافعة 20x | بدائل فقط")
    print("  ⚠️ أموال وهمية — لحمايتك")
    print("=" * 62)
    cap, trades, wins, peak, hist, status = run()
    wr = wins / trades * 100 if trades else 0
    print("=" * 62)
    print(f"  النتيجة النهائية : {status}")
    print(f"  10$ أصبحت        : {cap:.2f}$")
    print(f"  أعلى ذروة        : {peak:.2f}$")
    print(f"  عدد الصفقات      : {trades} | نسبة النجاح: {wr:.0f}%")
    print("=" * 62)
