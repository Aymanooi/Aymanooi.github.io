"""
جلب بيانات الشموع التاريخية من OKX (بيانات عامة، لا تحتاج مفاتيح API).
"""
import time
import requests
import pandas as pd

import config


def _parse_candles(raw):
    """تحويل استجابة OKX الخام إلى DataFrame مرتّب تصاعديًا بالوقت."""
    cols = ["ts", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(raw, columns=cols)
    # OKX يعيد القيم كنصوص — نحوّل الأعمدة الرقمية
    for c in ["open", "high", "low", "close", "vol"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(pd.to_numeric(df["ts"]), unit="ms", utc=True)
    df = df[["ts", "open", "high", "low", "close", "vol"]]
    return df.sort_values("ts").reset_index(drop=True)


def fetch_candles(symbol, bar=None, limit=None):
    """
    جلب آخر مجموعة شموع لزوج معيّن.
    يُستخدم في وضع التداول الحي/المحاكاة.
    """
    bar = bar or config.TIMEFRAME
    limit = limit or config.CANDLE_LIMIT
    url = f"{config.OKX_BASE_URL}/api/v5/market/candles"
    params = {"instId": symbol, "bar": bar, "limit": limit}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != "0":
        raise RuntimeError(f"OKX error for {symbol}: {payload.get('msg')}")
    return _parse_candles(payload["data"])


def fetch_history(symbol, bar=None, total=1500):
    """
    جلب تاريخ طويل عبر التصفّح للخلف (pagination) باستخدام نقطة history-candles.
    يُستخدم في الاختبار التاريخي (Backtest).
    """
    bar = bar or config.TIMEFRAME
    url = f"{config.OKX_BASE_URL}/api/v5/market/history-candles"
    all_rows = []
    after = None  # نطلب الشموع الأقدم من هذا الطابع الزمني

    while len(all_rows) < total:
        params = {"instId": symbol, "bar": bar, "limit": 100}
        if after:
            params["after"] = after
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") != "0":
            raise RuntimeError(f"OKX error for {symbol}: {payload.get('msg')}")
        data = payload["data"]
        if not data:
            break
        all_rows.extend(data)
        # أقدم طابع زمني في الدفعة (آخر صف لأن OKX يعيد تنازليًا)
        after = data[-1][0]
        time.sleep(0.15)  # احترام حدود الطلبات

    df = _parse_candles(all_rows)
    return df.drop_duplicates(subset="ts").reset_index(drop=True)


if __name__ == "__main__":
    # اختبار سريع
    df = fetch_history("BTC-USDT", total=300)
    print(f"تم جلب {len(df)} شمعة لـ BTC-USDT")
    print(df.head())
    print(df.tail())
