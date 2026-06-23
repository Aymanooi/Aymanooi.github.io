"""
Multi-Signal Confluence System (MSCS)
8 indicators + multi-timeframe + dynamic ATR-based SL/TP + market regime detection
"""
import numpy as np
from typing import List, Optional, Dict, Tuple


# ─── Core Math ────────────────────────────────────────────────────────────────

def ema(values: List[float], period: int) -> List[float]:
    k = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = np.mean(gains[:period])
    al = np.mean(losses[:period])
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    return 100.0 if al == 0 else 100 - (100 / (1 + ag / al))


def macd(closes: List[float], fast=12, slow=26, sig=9) -> Tuple[float, float, float]:
    if len(closes) < slow + sig:
        return 0.0, 0.0, 0.0
    ef = ema(closes, fast)
    es = ema(closes, slow)
    ml = [f - s for f, s in zip(ef, es)]
    sl = ema(ml, sig)
    return ml[-1], sl[-1], ml[-1] - sl[-1]


def bollinger(closes: List[float], period=20, std_k=2.0) -> Tuple[float, float, float]:
    w = closes[-period:] if len(closes) >= period else closes
    mid = float(np.mean(w))
    std = float(np.std(w))
    return mid + std_k * std, mid, mid - std_k * std


def atr(highs: List[float], lows: List[float], closes: List[float], period=14) -> float:
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    if not trs:
        return highs[-1] - lows[-1]
    v = float(np.mean(trs[:period]))
    for t in trs[period:]:
        v = (v * (period - 1) + t) / period
    return v


def adx(highs: List[float], lows: List[float], closes: List[float], period=14) -> float:
    if len(closes) < period * 2:
        return 20.0
    pdm, mdm, trs = [], [], []
    for i in range(1, len(closes)):
        hd = highs[i] - highs[i - 1]
        ld = lows[i - 1] - lows[i]
        pdm.append(hd if hd > ld and hd > 0 else 0)
        mdm.append(ld if ld > hd and ld > 0 else 0)
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))

    def smooth(arr, p):
        s = sum(arr[:p])
        out = [s]
        for v in arr[p:]:
            s = s - s / p + v
            out.append(s)
        return out

    st = smooth(trs, period)
    sp = smooth(pdm, period)
    sm = smooth(mdm, period)
    dxs = []
    for p, m, t in zip(sp, sm, st):
        di_p = 100 * p / t if t else 0
        di_m = 100 * m / t if t else 0
        dxs.append(abs(di_p - di_m) / (di_p + di_m) * 100 if (di_p + di_m) else 0)
    return float(np.mean(dxs[-period:])) if len(dxs) >= period else float(np.mean(dxs))


def stochastic(highs: List[float], lows: List[float], closes: List[float],
               k=14, d=3) -> Tuple[float, float]:
    if len(closes) < k:
        return 50.0, 50.0
    lowest  = min(lows[-k:])
    highest = max(highs[-k:])
    k_val = (closes[-1] - lowest) / (highest - lowest) * 100 if highest != lowest else 50.0
    d_val = k_val  # simplified
    return k_val, d_val


def volume_ratio(volumes: List[float], period=20) -> float:
    if len(volumes) < period + 1:
        return 1.0
    avg = float(np.mean(volumes[-period - 1:-1]))
    return volumes[-1] / avg if avg else 1.0


def detect_pattern(opens: List[float], highs: List[float],
                   lows: List[float], closes: List[float]) -> int:
    """Returns +1 bullish, -1 bearish, 0 neutral"""
    if len(closes) < 3:
        return 0
    o1, h1, l1, c1 = opens[-2], highs[-2], lows[-2], closes[-2]
    o2, h2, l2, c2 = opens[-1], highs[-1], lows[-1], closes[-1]
    b1 = abs(c1 - o1)
    b2 = abs(c2 - o2)
    r2 = h2 - l2

    # Bullish Engulfing
    if c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1 and b2 > b1 * 1.1:
        return 1
    # Bearish Engulfing
    if c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1 and b2 > b1 * 1.1:
        return -1
    if r2 > 0:
        lo_shadow = min(o2, c2) - l2
        hi_shadow = h2 - max(o2, c2)
        # Hammer
        if lo_shadow > 2 * b2 and hi_shadow < b2 * 0.3:
            return 1
        # Shooting Star
        if hi_shadow > 2 * b2 and lo_shadow < b2 * 0.3:
            return -1
        # Marubozu (strong candle, no shadows)
        if b2 / r2 > 0.85:
            return 1 if c2 > o2 else -1
    # Morning Star (3-candle)
    if len(closes) >= 3:
        o0, c0 = opens[-3], closes[-3]
        if c0 < o0 and abs(c1 - o1) < abs(c0 - o0) * 0.3 and c2 > o2 and c2 > (o0 + c0) / 2:
            return 1
        if c0 > o0 and abs(c1 - o1) < abs(c0 - o0) * 0.3 and c2 < o2 and c2 < (o0 + c0) / 2:
            return -1
    return 0


# ─── Master Scoring Engine ─────────────────────────────────────────────────────

def parse_candles(raw):
    """OKX returns newest first → reverse to oldest first"""
    raw = list(reversed(raw))
    return (
        [float(c[1]) for c in raw],   # opens
        [float(c[2]) for c in raw],   # highs
        [float(c[3]) for c in raw],   # lows
        [float(c[4]) for c in raw],   # closes
        [float(c[5]) for c in raw],   # volumes
    )


def analyze(candles_15m, candles_1h=None) -> Dict:
    """
    Full multi-indicator analysis.
    Returns: {signal, score, atr, sl_price, tp_price, details}
    score range: -100 to +100
    """
    if len(candles_15m) < 35:
        return {"signal": None, "score": 0, "atr": 0, "details": {}}

    opens, highs, lows, closes, volumes = parse_candles(candles_15m)
    price = closes[-1]
    details = {}
    total = 0

    # ── 1. EMA Trend  (max ±25) ──────────────────────────────
    e9   = ema(closes, 9)
    e21  = ema(closes, 21)
    e50  = ema(closes, 50) if len(closes) >= 50 else ema(closes, 21)
    e200 = ema(closes, 200) if len(closes) >= 200 else e50

    cross = 0
    if e9[-2] < e21[-2] and e9[-1] > e21[-1]:
        cross = 15
    elif e9[-2] > e21[-2] and e9[-1] < e21[-1]:
        cross = -15

    trend_50  = 5 if price > e50[-1] else -5
    trend_200 = 5 if price > e200[-1] else -5

    ema_score = cross + trend_50 + trend_200
    details["EMA"] = ema_score
    total += ema_score

    # ── 2. RSI  (max ±20) ────────────────────────────────────
    rsi_val = rsi(closes, 14)
    if rsi_val <= 25:
        rsi_score = 20
    elif rsi_val <= 35:
        rsi_score = 12
    elif rsi_val <= 45:
        rsi_score = 5
    elif rsi_val >= 75:
        rsi_score = -20
    elif rsi_val >= 65:
        rsi_score = -12
    elif rsi_val >= 55:
        rsi_score = -5
    else:
        rsi_score = 0
    details["RSI"] = rsi_score
    details["RSI_val"] = round(rsi_val, 1)
    total += rsi_score

    # ── 3. MACD  (max ±20) ───────────────────────────────────
    ml, sl_m, hist = macd(closes)
    macd_score = 0
    if hist > 0:
        macd_score += 10
    elif hist < 0:
        macd_score -= 10
    if ml > 0:
        macd_score += 5
    elif ml < 0:
        macd_score -= 5
    # Histogram acceleration
    _, _, hist_prev = macd(closes[:-1]) if len(closes) > 1 else (0, 0, hist)
    if hist > hist_prev and hist > 0:
        macd_score += 5
    elif hist < hist_prev and hist < 0:
        macd_score -= 5
    details["MACD"] = macd_score
    total += macd_score

    # ── 4. Bollinger Bands  (max ±15) ────────────────────────
    bb_up, bb_mid, bb_low = bollinger(closes)
    bb_width = (bb_up - bb_low) / bb_mid if bb_mid else 0
    if price <= bb_low:
        bb_score = 15
    elif price <= bb_mid:
        bb_score = 5
    elif price >= bb_up:
        bb_score = -15
    elif price >= bb_mid:
        bb_score = -5
    else:
        bb_score = 0
    details["BB"] = bb_score
    details["BB_width"] = round(bb_width * 100, 2)
    total += bb_score

    # ── 5. Stochastic  (max ±10) ─────────────────────────────
    k_val, _ = stochastic(highs, lows, closes)
    if k_val < 20:
        stoch_score = 10
    elif k_val < 35:
        stoch_score = 5
    elif k_val > 80:
        stoch_score = -10
    elif k_val > 65:
        stoch_score = -5
    else:
        stoch_score = 0
    details["Stoch"] = stoch_score
    details["Stoch_val"] = round(k_val, 1)
    total += stoch_score

    # ── 6. Volume Confirmation  (max ±10) ────────────────────
    vol = volume_ratio(volumes)
    if vol > 2.5:
        vol_score = 10 * (1 if total > 0 else -1)
    elif vol > 1.5:
        vol_score = 5 * (1 if total > 0 else -1)
    else:
        vol_score = 0
    details["Volume"] = vol_score
    details["Vol_ratio"] = round(vol, 2)
    total += vol_score

    # ── 7. Candlestick Patterns  (max ±10) ───────────────────
    pat = detect_pattern(opens, highs, lows, closes)
    pat_score = pat * 10
    details["Pattern"] = pat_score
    total += pat_score

    # ── 8. ADX Market Regime  (multiplier) ───────────────────
    adx_val = adx(highs, lows, closes)
    details["ADX"] = round(adx_val, 1)
    if adx_val > 35:
        total = int(total * 1.35)
    elif adx_val > 25:
        total = int(total * 1.15)
    elif adx_val > 20:
        total = int(total * 0.85)
    elif adx_val > 15:
        total = int(total * 0.65)
    else:
        total = int(total * 0.45)

    # ── 9. Higher Timeframe (1h) Confirmation  (max ±15) ────
    if candles_1h and len(candles_1h) >= 26:
        _, _, _, c1h, _ = parse_candles(candles_1h)
        e9_h  = ema(c1h, 9)
        e21_h = ema(c1h, 21)
        rsi_h = rsi(c1h, 14)
        ml_h, _, hist_h = macd(c1h)

        htf = 0
        htf += 5 if e9_h[-1] > e21_h[-1] else -5
        htf += 5 if rsi_h > 50 else -5
        htf += 5 if hist_h > 0 else -5
        details["HTF_1h"] = htf

        # إذا كان الـ HTF مخالفاً تماماً للإشارة → يلغي الصفقة
        htf_contradicts = (total > 0 and htf <= -10) or (total < 0 and htf >= 10)
        if htf_contradicts:
            return {
                "signal": None, "score": 0, "atr": 0.0,
                "sl_price": 0.0, "tp_price": 0.0, "price": price, "details": details,
            }
        total += htf

    # ── Clamp & Decide ───────────────────────────────────────
    total = max(-100, min(100, total))
    details["Score"] = total

    # RR=3:1 → WR breakeven = 25% فقط، عتبة 40 تعطي إشارات أكثر مع الحفاظ على الجودة
    THRESHOLD = 40
    signal = None
    if total >= THRESHOLD:
        signal = "buy"
    elif total <= -THRESHOLD:
        signal = "sell"

    # SL=1.5×ATR / TP=4.5×ATR → RR=3:1 → WR مطلوب 25% فقط
    atr_val = atr(highs, lows, closes, 14)
    if signal == "buy":
        sl_price = round(price - 1.5 * atr_val, 6)
        tp_price = round(price + 4.5 * atr_val, 6)
    elif signal == "sell":
        sl_price = round(price + 1.5 * atr_val, 6)
        tp_price = round(price - 4.5 * atr_val, 6)
    else:
        sl_price = tp_price = 0.0

    return {
        "signal":   signal,
        "score":    total,
        "atr":      round(atr_val, 6),
        "sl_price": sl_price,
        "tp_price": tp_price,
        "price":    price,
        "details":  details,
    }


def get_signal(candles_15m, candles_1h=None, **kwargs):
    """Backward-compatible simple wrapper"""
    r = analyze(candles_15m, candles_1h)
    return r["signal"]
