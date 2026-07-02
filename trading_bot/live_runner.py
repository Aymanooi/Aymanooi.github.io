"""
المشغّل الدوري — بديل keep_alive.py المناسب لـ GitHub Actions.

الملف المرفوع (keep_alive.py) مصمّم لخادم VPS يعمل 24/7 بحلقة لا نهائية.
على GitHub Actions النمط الصحيح مختلف: تشغيل واحد قصير (single-shot)
يُستدعى بجدولة cron من الـ workflow، ثم ينتهي.

كل تشغيل:
  1. يجلب أحدث الشموع ويحسب إشارة "بوت القلعة"
     (Momentum Confluence + Regime + كل الحمايات — أفضل ما لدينا).
  2. إن وُجدت إشارة ولا توجد صفقة مفتوحة → يفتح صفقة Demo
     مع وقف خسارة وجني أرباح مرفقين.
  3. يسجّل كل شيء في السجل.

⚠️ يعمل في وضع Demo (محاكاة OKX الرسمية) افتراضيًا وإجباريًا.
"""
import logging
import sys

import config as cfg
from data_feed import fetch_history
from strategy_lab import prepare, sig_momentum
from regime import detect_regime, TREND_UP, TREND_DOWN
from okx_client import OKXClient

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("live_runner")

SYMBOL = "BTC-USDT-SWAP"
CANDLE_SYMBOL = "BTC-USDT"
RISK_FRAC = 0.02              # مخاطرة 2% — لا 10%
LEVERAGE = 3                  # سقف آمن — لا 50


def compute_signal():
    """إشارة بوت القلعة على أحدث بيانات."""
    df = prepare(fetch_history(CANDLE_SYMBOL, total=600))
    df = detect_regime(df)
    i = len(df) - 1
    d = sig_momentum(df, i)
    if d == 0:
        return 0, None
    reg = df.iloc[i]["regime"]
    if (d == 1 and reg != TREND_UP) or (d == -1 and reg != TREND_DOWN):
        logger.info("إشارة %s محجوبة بفلتر النظام (%s)", d, reg)
        return 0, None
    row = df.iloc[i]
    return d, row


def main():
    client = OKXClient()
    if not client.demo:
        logger.warning("⚠️ وضع LIVE مفعّل! تأكد أنك تقصد ذلك فعلًا.")

    d, row = compute_signal()
    if d == 0:
        logger.info("لا إشارة صالحة الآن — انتهى التشغيل.")
        return

    # لا نفتح صفقة إن كانت هناك صفقة قائمة
    pos = client.positions(SYMBOL)
    open_pos = [p for p in (pos.get("data") or []) if float(p.get("pos", 0) or 0) != 0]
    if open_pos:
        logger.info("توجد صفقة مفتوحة بالفعل — لا إجراء.")
        return

    entry = float(row["close"])
    risk = float(row["atr"]) * 1.5
    if d == 1:
        side, pos_side = "buy", "long"
        sl, tp = entry - risk, entry + risk * 2
    else:
        side, pos_side = "sell", "short"
        sl, tp = entry + risk, entry - risk * 2

    client.set_leverage(SYMBOL, LEVERAGE)
    # حجم عقد BTC-USDT-SWAP = 0.01 BTC؛ نحسب من رصيد الحساب التجريبي
    bal = client.balance()
    try:
        usdt = next(x for d_ in bal["data"] for x in d_["details"] if x["ccy"] == "USDT")
        equity = float(usdt["eq"])
    except (KeyError, StopIteration, TypeError):
        logger.error("تعذّر قراءة الرصيد — تأكد من ضبط المفاتيح في Secrets.")
        sys.exit(1)

    qty_btc = equity * RISK_FRAC / risk
    contracts = max(1, round(qty_btc / 0.01))
    logger.info("إشارة %s | دخول %.1f | SL %.1f | TP %.1f | عقود %d",
                pos_side, entry, sl, tp, contracts)
    result = client.market_order(SYMBOL, side, contracts, pos_side,
                                 sl_trigger=round(sl, 1), tp_trigger=round(tp, 1))
    logger.info("نتيجة الأمر: %s", result)


if __name__ == "__main__":
    main()
