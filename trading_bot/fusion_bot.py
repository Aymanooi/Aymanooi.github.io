"""
❄️⚡ FUSION — بوت الاندماج النهائي ⚡❄️
دمج بوتات المستخدم الثلاثة (super_bot, advanced_bot, Snowball v22)
مع مختبر التداول الكمّي — رأس مال 10$.

═══ ما أُخذ من كل بوت (وما استُبعد ولماذا) ═══
  super_bot    ✅ نواة عميل OKX الموقّع (مُصلحة في okx_client.py)
               ❌ استراتيجية نطاق 24h (قيست: -7.9%)
  advanced_bot ✅ مراقب التراجع + شروط الإيقاف (مُصلحة بتتبع PnL حقيقي)
               ❌ عدّاد الأرباح المختلق + تصويت الوكلاء (قيس: -13.6%)
  Snowball v22 ✅ مسح متعدد العملات + سلّم قواطع الدارة + عقيدة Paper-First
               ❌ إطار الدقيقة (الرسوم = 1.0x الوقف) + رافعة 20x المتصاعدة
  المختبر      ✅ إشارة القلعة (زخم متعدد العوامل + فلتر نظام السوق)
               ✅ وقف/هدف ATR + رافعة بسقف حاكم البيانات (3x)
               ✅ بوابة APEX للترقية إلى المال الحقيقي

═══ عقيدة الترقية (الدمج الذكي الحقيقي) ═══
  وضع Demo (الافتراضي): يتداول بحرية بأموال OKX التجريبية —
     وبذلك يجمع سجلّ أداء حقيقي خارج العيّنة تلقائيًا.
  وضع LIVE: مقفول بشرطين معًا:
     ① OKX_LIVE=I_ACCEPT_FULL_RISK في البيئة (قرارك الصريح)
     ② سجلّ الـ Demo المتراكم يجتاز بوابة APEX الإحصائية
  البوت يبني بنفسه الدليل الذي يرقّيه. لا ترقية بلا برهان.

التشغيل: python fusion_bot.py          (دورة واحدة — متوافق مع Actions)
         بلا مفاتيح → وضع استطلاع يطبع القرارات فقط.
"""
import json
import logging
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config as cfg
from data_feed import fetch_history
from strategy_lab import prepare, sig_momentum
from regime import detect_regime, TREND_UP, TREND_DOWN
from okx_client import OKXClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fusion")

# ═══ إعدادات الاندماج ═══
CAPITAL = 10.0                     # 💰 رأس المال المستهدف
# قائمة Snowball (بدون إطار الدقيقة القاتل — نعمل على الساعة)
SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "BNB-USDT", "XRP-USDT",
           "DOGE-USDT", "ADA-USDT", "AVAX-USDT", "LINK-USDT"]
SWAP = {s: s + "-SWAP" for s in SYMBOLS}
MAX_POSITIONS = 2                  # صفقتان متزامنتان كحد أقصى (لا 10)
RISK_FRAC = 0.02                   # 2% مخاطرة (لا 4%)
LEVERAGE = 3                       # سقف حاكم الرافعة (لا 20x)
# سلّم قواطع الدارة من Snowball (مُشدَّد):
CB_WARN, CB_HALF, CB_HALT = 0.05, 0.10, 0.20   # تحذير/نصف مخاطرة/إيقاف
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "fusion_state.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"peak_equity": CAPITAL, "trades": [], "halted": False}


def save_state(st):
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=1, default=str)


def drawdown_governor(equity, st):
    """من advanced_bot (مُصلح) + سلّم Snowball: يحكم المخاطرة بالتراجع."""
    st["peak_equity"] = max(st.get("peak_equity", equity), equity)
    dd = 1 - equity / st["peak_equity"] if st["peak_equity"] > 0 else 0
    if dd >= CB_HALT:
        st["halted"] = True
        log.critical("🛑 قاطع الدارة: تراجع %.1f%% — إيقاف كامل", dd * 100)
        return 0.0
    if dd >= CB_HALF:
        log.warning("⚠️ تراجع %.1f%% — المخاطرة تُخفَّض للنصف", dd * 100)
        return RISK_FRAC * 0.5
    if dd >= CB_WARN:
        log.warning("⚠️ تراجع %.1f%% — مراقبة مشددة", dd * 100)
    return RISK_FRAC


def scan_signals():
    """مسح Snowball متعدد العملات — بإشارة القلعة المُختبرة (زخم+نظام)."""
    picks = []
    for s in SYMBOLS:
        try:
            df = prepare(fetch_history(s, total=600))
            df = detect_regime(df)
        except Exception as e:
            log.warning("تخطي %s: %s", s, e)
            continue
        i = len(df) - 1
        d = sig_momentum(df, i)
        if d == 0:
            continue
        reg = df.iloc[i]["regime"]
        if (d == 1 and reg == TREND_UP) or (d == -1 and reg == TREND_DOWN):
            row = df.iloc[i]
            if not pd.isna(row["atr"]) and row["atr"] > 0:
                picks.append({"symbol": s, "dir": d,
                              "close": float(row["close"]),
                              "atr": float(row["atr"]),
                              "mom": float(row.get("roc13", 0) or 0)})
    # الأقوى زخمًا أولًا (فلسفة Snowball في انتقاء الفرص)
    picks.sort(key=lambda p: abs(p["mom"]), reverse=True)
    return picks


def run_cycle():
    st = load_state()
    if st.get("halted"):
        log.critical("🛑 البوت موقوف بقاطع الدارة — تدخّل يدوي مطلوب (احذف fusion_state.json)")
        return

    client = OKXClient()
    has_keys = bool(client.api_key)
    mode = ("LIVE⚠️" if not client.demo else "DEMO") if has_keys else "استطلاع"
    log.info("═══ FUSION | وضع %s | رأس المال %s$ ═══", mode, CAPITAL)

    # الرصيد الحقيقي من OKX إن توفرت المفاتيح، وإلا الافتراضي
    equity = CAPITAL
    open_syms = set()
    if has_keys:
        try:
            bal = client.balance()
            usdt = next(x for d in bal["data"] for x in d["details"]
                        if x["ccy"] == "USDT")
            equity = float(usdt["eq"])
            pos = client.positions()
            open_syms = {p["instId"].replace("-SWAP", "")
                         for p in (pos.get("data") or [])
                         if float(p.get("pos", 0) or 0) != 0}
        except Exception as e:
            log.error("تعذر قراءة الحساب: %s", e)

    risk = drawdown_governor(equity, st)
    if risk == 0.0:
        save_state(st)
        return

    slots = MAX_POSITIONS - len(open_syms)
    log.info("الرصيد: %.2f$ | صفقات مفتوحة: %d | فتحات متاحة: %d",
             equity, len(open_syms), slots)

    if slots > 0:
        picks = [p for p in scan_signals() if p["symbol"] not in open_syms]
        log.info("إشارات صالحة بعد الفلاتر: %d", len(picks))
        for p in picks[:slots]:
            d, entry, atr_v = p["dir"], p["close"], p["atr"]
            risk_dist = atr_v * 1.5
            sl = entry - risk_dist * d
            tp = entry + risk_dist * 2 * d
            qty = min(equity, CAPITAL) * risk * LEVERAGE / entry
            tag = "LONG" if d == 1 else "SHORT"
            log.info("🎯 %s %s @ %.6g | SL %.6g | TP %.6g",
                     tag, p["symbol"], entry, sl, tp)
            st["trades"].append({"ts": str(datetime.now(timezone.utc)),
                                 "symbol": p["symbol"], "dir": tag,
                                 "entry": entry, "sl": sl, "tp": tp})
            if has_keys:
                inst = SWAP[p["symbol"]]
                client.set_leverage(inst, LEVERAGE)
                side = "buy" if d == 1 else "sell"
                pos_side = "long" if d == 1 else "short"
                client.market_order(inst, side, max(1, round(qty * 100)),
                                    pos_side, sl_trigger=sl, tp_trigger=tp)
    save_state(st)
    log.info("انتهت الدورة. السجل: %d قرارًا محفوظًا", len(st["trades"]))


if __name__ == "__main__":
    run_cycle()
