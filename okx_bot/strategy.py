import numpy as np


def ema(values, period):
    result = []
    k = 2 / (period + 1)
    ema_val = values[0]
    result.append(ema_val)
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return 50.0
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_signal(candles, ema_fast=9, ema_slow=21, rsi_period=14,
               rsi_buy_max=65, rsi_sell_min=35):
    """
    Returns: 'buy', 'sell', or None
    candles: list from OKX API [[ts, o, h, l, c, vol, volCcy], ...]
    """
    if len(candles) < ema_slow + 5:
        return None

    # OKX returns newest first → reverse to oldest first
    candles = list(reversed(candles))
    closes = [float(c[4]) for c in candles]

    ema_f = ema(closes, ema_fast)
    ema_s = ema(closes, ema_slow)
    rsi_val = rsi(closes, rsi_period)

    # Need at least 2 values to detect crossover
    if len(ema_f) < 2 or len(ema_s) < 2:
        return None

    prev_fast, curr_fast = ema_f[-2], ema_f[-1]
    prev_slow, curr_slow = ema_s[-2], ema_s[-1]

    bullish_cross = prev_fast < prev_slow and curr_fast > curr_slow
    bearish_cross = prev_fast > prev_slow and curr_fast < curr_slow

    if bullish_cross and rsi_val < rsi_buy_max:
        return "buy"
    if bearish_cross and rsi_val > rsi_sell_min:
        return "sell"
    return None
