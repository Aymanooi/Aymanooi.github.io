#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║  SNOWBALL PAPER v1.0 — نسخة نظيفة وصادقة من snowball_v22          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ⚠️  هذا النظام PAPER TRADING فقط — تداول وهمي 100%                ║
║      لا يوجد فيه أي كود لتنفيذ أوامر حقيقية، ولا يقبل مفاتيح API   ║
║      يستخدم أسعار OKX الحية الحقيقية (API عام، للقراءة فقط)        ║
║                                                                    ║
║  ما تم إصلاحه من النسخة الأصلية (6890 سطر):                        ║
║  🔧 النسخة الأصلية لم يكن فيها تنفيذ حقيقي أصلاً (لا يوجد else     ║
║     بعد if PAPER_TRADING) والرصيد الحقيقي كان مكتوباً = 0          ║
║  🔧 رافعة x20 ومخاطرة 7.5% → استبدلت بـ x3 و 1% (قابلة للنجاة)     ║
║  🔧 لا رسوم ولا انزلاق سعري في المحاكاة → أضيفت رسوم OKX الفعلية   ║
║     (Taker 0.05%) وانزلاق سعري لنتائج صادقة                        ║
║  🔧 تجاهل الحد الأدنى لحجم العقود → الآن يحترم مواصفات OKX          ║
║     الحقيقية (ctVal/lotSz/minSz) ويرفض الصفقات المستحيلة بصدق      ║
║  🔧 شموع دقيقة + دورة 5 ثوانٍ (إفلاس بالرسوم) → شموع 5 دقائق       ║
║     ودورة كل 60 ثانية                                              ║
║  🔧 عتبة إجماع 52% (عملة معدنية) → 65%                             ║
║  🔧 محاكاة تصفية (Liquidation) واقعية للرافعة المعزولة             ║
║  🔧 اكتشاف تلقائي للعملات: سيولة 24h ≥ $30M من السوق الحي،         ║
║     بدون BTC/ETH/SOL وبدون الأصول المرمّزة (ذهب/أسهم)، تحديث كل    ║
║     ساعة، والعملة ذات الصفقة المفتوحة لا تُسقط من المراقبة          ║
║                                                                    ║
║  التشغيل:                                                          ║
║    python3 snowball_paper.py --once            # دورة واحدة        ║
║    python3 snowball_paper.py --minutes 60      # ساعة كاملة        ║
║    python3 snowball_paper.py --balance 2       # برصيدك الحقيقي    ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
import math
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

log = logging.getLogger("snowball")

OKX_BASE = "https://www.okx.com"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snowball_paper.db")


# ══════════════════════════════════════════════════════════════════
# ⚙️ الإعدادات — قيم قابلة للنجاة، لا قيم "خارقة"
# ══════════════════════════════════════════════════════════════════
@dataclass
class Config:
    # ── اكتشاف العملات ديناميكياً حسب السيولة الحقيقية ──────────
    SYMBOLS: List[str] = field(default_factory=list)  # تُملأ تلقائياً من السوق
    MIN_LIQUIDITY_USD: float = 30_000_000  # حجم تداول 24h لا يقل عن $30M
    MAX_SYMBOLS: int = 20                  # سقف للعدد (احترام حدود الـ API)
    SYMBOL_REFRESH_CYCLES: int = 60        # إعادة اكتشاف القائمة كل ساعة
    EXCLUDED_BASES: frozenset = frozenset({"BTC", "ETH", "SOL"})  # مستبعدة بطلبك
    # أصول مرمّزة ليست عملات رقمية (ذهب/فضة/أسهم) — خارج نطاق "العملات الرقمية"
    NON_CRYPTO_BASES: frozenset = frozenset({
        "XAU", "XAG", "MU", "SNDK", "SOXL", "MSTR", "SKHYNIX",
        "DRAM", "SPCX", "OPENAI", "COIN", "HOOD", "NVDA", "TSLA",
        "AAPL", "GOOGL", "META", "AMZN", "MSFT", "CRCL", "SBET",
    })
    BAR: str = "5m"              # شموع 5 دقائق — لا سكالبينغ انتحاري
    LOOKBACK: int = 200          # عدد الشموع للتحليل
    CYCLE_SECONDS: int = 60      # دورة كل دقيقة

    PAPER_BALANCE: float = 100.0  # الرصيد الوهمي الافتراضي (--balance لتغييره)
    LEVERAGE: int = 3             # رافعة متواضعة — النسخة الأصلية x20 كانت انتحاراً
    RISK_PCT: float = 0.01        # 1% مخاطرة لكل صفقة
    MAX_RISK_PCT: float = 0.02    # سقف المخاطرة مع سلسلة الانتصارات
    MIN_RISK_PCT: float = 0.005   # أرضية المخاطرة مع سلسلة الخسائر
    MAX_POSITIONS: int = 3
    MAX_MARGIN_PCT: float = 0.30  # لا تحجز أكثر من 30% من الرصيد كهامش لصفقة

    TAKER_FEE: float = 0.0005     # رسوم OKX Futures Taker الفعلية 0.05%
    SLIPPAGE: float = 0.0002      # انزلاق سعري 0.02% لكل تنفيذ

    SL_ATR: float = 1.5           # وقف الخسارة = 1.5 × ATR
    TP_ATR: float = 3.0           # الهدف = 3 × ATR (نسبة عائد/مخاطرة 1:2)
    TRAIL_ATR: float = 1.2        # وقف متحرك بعد الدخول في ربح
    BREAKEVEN_ATR: float = 1.0    # نقل SL لنقطة الدخول بعد ربح 1×ATR

    MIN_AGREEMENT: float = 0.65   # إجماع الوكلاء المطلوب (الأصلية: 52% = عملة معدنية)
    MIN_ACTIVE_AGENTS: int = 3    # أقل عدد وكلاء عندهم رأي

    DAILY_LOSS_HALT: float = 0.05  # خسارة يومية 5% → توقف عن فتح صفقات لليوم
    MAX_DRAWDOWN_HALT: float = 0.15  # سحب 15% من القمة → إيقاف كامل


config = Config()


# ══════════════════════════════════════════════════════════════════
# 🌐 عميل OKX — قراءة فقط، لا مفاتيح، لا أوامر
# ══════════════════════════════════════════════════════════════════
class OKXPublic:
    def __init__(self):
        self.s = requests.Session()
        self.specs: Dict[str, dict] = {}

    def _get(self, path: str, params: dict) -> Optional[list]:
        for attempt in range(3):
            try:
                r = self.s.get(OKX_BASE + path, params=params, timeout=15)
                j = r.json()
                if j.get("code") == "0":
                    return j["data"]
                log.warning(f"OKX {path}: {j.get('msg')}")
            except Exception as e:
                log.warning(f"OKX {path} محاولة {attempt+1}: {e}")
                time.sleep(1 + attempt)
        return None

    def load_specs(self, symbols: List[str]) -> None:
        """مواصفات العقود الحقيقية — حتى تكون المحاكاة صادقة مع الواقع"""
        data = self._get("/api/v5/public/instruments", {"instType": "SWAP"}) or []
        for d in data:
            if d["instId"] in symbols:
                self.specs[d["instId"]] = {
                    "ctVal": float(d["ctVal"]),      # قيمة العقد الواحد بالعملة الأساس
                    "lotSz": float(d["lotSz"]),      # أصغر زيادة في عدد العقود
                    "minSz": float(d["minSz"]),      # أقل عدد عقود مسموح
                    "maxLever": float(d["lever"]),
                }

    def discover_symbols(self) -> List[str]:
        """اكتشاف العملات المؤهلة من السوق الحي: سيولة 24h ≥ الحد الأدنى،
        بدون BTC/ETH/SOL وبدون الأصول المرمّزة غير الرقمية"""
        data = self._get("/api/v5/market/tickers", {"instType": "SWAP"}) or []
        rows = []
        for d in data:
            inst = d["instId"]
            if not inst.endswith("-USDT-SWAP"):
                continue
            base = inst.split("-")[0]
            if base in config.EXCLUDED_BASES or base in config.NON_CRYPTO_BASES:
                continue
            try:
                vol_usd = float(d["volCcy24h"]) * float(d["last"])
            except (ValueError, KeyError):
                continue
            if vol_usd >= config.MIN_LIQUIDITY_USD:
                rows.append((inst, vol_usd))
        rows.sort(key=lambda x: -x[1])
        symbols = [r[0] for r in rows[:config.MAX_SYMBOLS]]
        log.info(f"🔍 اكتشاف السوق: {len(rows)} عملة سيولتها ≥ "
                 f"${config.MIN_LIQUIDITY_USD/1e6:.0f}M — اخترت أعلى {len(symbols)}")
        for inst, vol in rows[:config.MAX_SYMBOLS]:
            log.info(f"   {inst.split('-')[0]:<10} ${vol/1e6:,.0f}M/24h")
        return symbols

    def candles(self, symbol: str, bar: str, limit: int) -> Optional[List[dict]]:
        """شموع من الأحدث للأقدم في API → نعكسها للأقدم أولاً"""
        data = self._get("/api/v5/market/candles",
                         {"instId": symbol, "bar": bar, "limit": str(limit)})
        if not data:
            return None
        out = []
        for row in reversed(data):
            out.append({
                "ts": int(row[0]), "o": float(row[1]), "h": float(row[2]),
                "l": float(row[3]), "c": float(row[4]), "v": float(row[5]),
                "confirmed": row[8] == "1",
            })
        return out

    def price(self, symbol: str) -> Optional[float]:
        data = self._get("/api/v5/market/ticker", {"instId": symbol})
        if data:
            return float(data[0]["last"])
        return None

    def history_candles(self, symbol: str, bar: str, days: int) -> List[dict]:
        """جلب تاريخ كامل بالتقسيم — لأغراض المحاكاة التاريخية (Backtest)"""
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - days * 24 * 3600 * 1000
        out, after = [], str(end_ms)
        while True:
            data = self._get("/api/v5/market/history-candles",
                             {"instId": symbol, "bar": bar,
                              "after": after, "limit": "100"})
            if not data:
                break
            for row in data:  # الأحدث أولاً
                ts = int(row[0])
                if ts < start_ms:
                    break
                out.append({"ts": ts, "o": float(row[1]), "h": float(row[2]),
                            "l": float(row[3]), "c": float(row[4]),
                            "v": float(row[5]), "confirmed": True})
            oldest = int(data[-1][0])
            if oldest < start_ms or len(data) < 100:
                break
            after = str(oldest)
            time.sleep(0.12)  # احترام حدود الـ API
        out.sort(key=lambda c: c["ts"])
        return out


# ══════════════════════════════════════════════════════════════════
# 📐 المؤشرات — بايثون خالص، بدون مكتبات ثقيلة
# ══════════════════════════════════════════════════════════════════
def ema(vals: List[float], period: int) -> List[float]:
    if not vals:
        return []
    k = 2.0 / (period + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes: List[float], period: int = 14) -> List[float]:
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    out = [50.0] * len(closes)
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / period, losses / period
    out[period] = 100 - 100 / (1 + (avg_g / avg_l if avg_l else 1e9))
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (period - 1) + max(d, 0)) / period
        avg_l = (avg_l * (period - 1) + max(-d, 0)) / period
        out[i] = 100 - 100 / (1 + (avg_g / avg_l if avg_l else 1e9))
    return out


def macd(closes: List[float]) -> Tuple[List[float], List[float]]:
    e12, e26 = ema(closes, 12), ema(closes, 26)
    line = [a - b for a, b in zip(e12, e26)]
    signal = ema(line, 9)
    return line, signal


def atr(candles: List[dict], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["h"], candles[i]["l"], candles[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    period = min(period, len(trs))
    return sum(trs[-period:]) / period


def bollinger(closes: List[float], period: int = 20) -> Tuple[float, float, float]:
    window = closes[-period:]
    mid = sum(window) / len(window)
    var = sum((c - mid) ** 2 for c in window) / len(window)
    sd = math.sqrt(var)
    return mid - 2 * sd, mid, mid + 2 * sd


# ══════════════════════════════════════════════════════════════════
# 🤖 الوكلاء — كل وكيل يرجّع (صوت: -1/0/+1، ثقة: 0..1)
# نفس فكرة النسخة الأصلية لكن بمنطق شفاف قابل للتدقيق
# ══════════════════════════════════════════════════════════════════
def agent_trend(closes: List[float]) -> Tuple[int, float]:
    """اتجاه: تقاطع EMA20/EMA50 مع تأكيد EMA100"""
    e20, e50, e100 = ema(closes, 20)[-1], ema(closes, 50)[-1], ema(closes, 100)[-1]
    price = closes[-1]
    if e20 > e50 > e100 and price > e20:
        return 1, min((e20 - e50) / e50 * 200, 1.0)
    if e20 < e50 < e100 and price < e20:
        return 1 * -1, min((e50 - e20) / e50 * 200, 1.0)
    return 0, 0.0


def agent_momentum(closes: List[float]) -> Tuple[int, float]:
    """زخم: MACD فوق/تحت خط الإشارة + اتجاه الهيستوغرام"""
    line, signal = macd(closes)
    hist_now, hist_prev = line[-1] - signal[-1], line[-2] - signal[-2]
    scale = abs(closes[-1]) * 0.001 or 1.0
    conf = min(abs(hist_now) / scale, 1.0)
    if hist_now > 0 and hist_now > hist_prev:
        return 1, conf
    if hist_now < 0 and hist_now < hist_prev:
        return -1, conf
    return 0, 0.0


def agent_rsi(closes: List[float]) -> Tuple[int, float]:
    """RSI: ارتداد من التشبع، حياد في المنتصف"""
    r = rsi(closes)[-1]
    if r < 30:
        return 1, (30 - r) / 30
    if r > 70:
        return -1, (r - 70) / 30
    return 0, 0.0


def agent_volume(candles: List[dict]) -> Tuple[int, float]:
    """حجم: شمعة بحجم ضعف المتوسط تأخذ اتجاه جسمها"""
    vols = [c["v"] for c in candles[-21:-1]]
    avg = sum(vols) / len(vols) if vols else 0
    last = candles[-1]
    if avg <= 0 or last["v"] < 2 * avg:
        return 0, 0.0
    conf = min(last["v"] / (avg * 4), 1.0)
    if last["c"] > last["o"]:
        return 1, conf
    if last["c"] < last["o"]:
        return -1, conf
    return 0, 0.0


def agent_bollinger(closes: List[float]) -> Tuple[int, float]:
    """تقلب: كسر النطاق مع اتجاهه (momentum breakout)"""
    lower, mid, upper = bollinger(closes)
    price, prev = closes[-1], closes[-2]
    width = (upper - lower) / mid if mid else 0
    conf = min(width * 20, 1.0)
    if prev <= upper < price:
        return 1, conf
    if prev >= lower > price:
        return -1, conf
    return 0, 0.0


AGENTS = [
    ("Trend", 3.0, lambda c, k: agent_trend([x["c"] for x in k])),
    ("Momentum", 2.5, lambda c, k: agent_momentum([x["c"] for x in k])),
    ("RSI", 2.0, lambda c, k: agent_rsi([x["c"] for x in k])),
    ("Volume", 2.0, lambda c, k: agent_volume(k)),
    ("Bollinger", 2.0, lambda c, k: agent_bollinger([x["c"] for x in k])),
]


def council_vote(candles: List[dict]) -> Tuple[str, float, dict]:
    """تصويت مرجّح — يتطلب إجماعاً حقيقياً لا 52%"""
    details, w_long, w_short, w_total, active = {}, 0.0, 0.0, 0.0, 0
    for name, weight, fn in AGENTS:
        vote, conf = fn(None, candles)
        details[name] = {"vote": vote, "conf": round(conf, 2)}
        w_total += weight
        if vote != 0:
            active += 1
            if vote > 0:
                w_long += weight * conf
            else:
                w_short += weight * conf
    if active < config.MIN_ACTIVE_AGENTS:
        return "NONE", 0.0, details
    denom = w_long + w_short
    if denom <= 0:
        return "NONE", 0.0, details
    if w_long > w_short:
        agreement = w_long / denom
        return ("LONG", agreement, details) if agreement >= config.MIN_AGREEMENT else ("NONE", agreement, details)
    agreement = w_short / denom
    return ("SHORT", agreement, details) if agreement >= config.MIN_AGREEMENT else ("NONE", agreement, details)


# ══════════════════════════════════════════════════════════════════
# 🛡️ إدارة المخاطر — النسخة القابلة للنجاة
# ══════════════════════════════════════════════════════════════════
class RiskManager:
    def __init__(self, start_balance: float):
        self.start = start_balance
        self.peak = start_balance
        self.win_streak = 0
        self.loss_streak = 0
        self.day = datetime.now(timezone.utc).date()
        self.day_start_equity = start_balance
        self.halted_today = False
        self.halted_forever = False

    def new_day_check(self, equity: float, today=None) -> None:
        today = today or datetime.now(timezone.utc).date()
        if today != self.day:
            self.day = today
            self.day_start_equity = equity
            self.halted_today = False

    def record(self, pnl: float, equity: float) -> None:
        self.peak = max(self.peak, equity)
        if pnl > 0:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        # كسر الحماية اليومي
        if equity <= self.day_start_equity * (1 - config.DAILY_LOSS_HALT):
            self.halted_today = True
            log.warning(f"🛑 خسارة يومية تجاوزت {config.DAILY_LOSS_HALT:.0%} — لا صفقات جديدة اليوم")
        # كسر الحماية الكلي
        if equity <= self.peak * (1 - config.MAX_DRAWDOWN_HALT):
            self.halted_forever = True
            log.warning(f"🛑 السحب تجاوز {config.MAX_DRAWDOWN_HALT:.0%} من القمة — إيقاف كامل")

    def can_open(self) -> bool:
        return not (self.halted_today or self.halted_forever)

    def risk_pct(self) -> float:
        r = config.RISK_PCT + self.win_streak * 0.0025 - self.loss_streak * 0.0025
        return max(config.MIN_RISK_PCT, min(r, config.MAX_RISK_PCT))


# ══════════════════════════════════════════════════════════════════
# 💼 الوسيط الوهمي — رسوم وانزلاق وتصفية حقيقية، فلوس وهمية
# ══════════════════════════════════════════════════════════════════
class PaperBroker:
    def __init__(self, balance: float, specs: Dict[str, dict]):
        self.balance = balance          # الرصيد الحر
        self.specs = specs
        self.positions: Dict[str, dict] = {}
        self.next_id = 1
        self.fees_paid = 0.0
        self.trades: List[dict] = []

    def equity(self, prices: Dict[str, float]) -> float:
        eq = self.balance
        for p in self.positions.values():
            price = prices.get(p["symbol"], p["entry"])
            sign = 1 if p["dir"] == "LONG" else -1
            eq += p["margin"] + sign * (price - p["entry"]) * p["qty"]
        return eq

    def size_position(self, symbol: str, price: float, sl_dist: float,
                      risk_usdt: float) -> Tuple[float, Optional[str]]:
        """حجم الصفقة وفق مواصفات العقد الحقيقية — أو سبب الرفض بصدق"""
        spec = self.specs.get(symbol)
        if not spec:
            return 0.0, "لا توجد مواصفات للعقد"
        qty_raw = risk_usdt / sl_dist                     # كمية بالعملة الأساس
        contracts = qty_raw / spec["ctVal"]
        contracts = math.floor(contracts / spec["lotSz"]) * spec["lotSz"]
        if contracts < spec["minSz"]:
            min_notional = spec["minSz"] * spec["ctVal"] * price
            return 0.0, (f"الرصيد أصغر من الحد الأدنى للعقد "
                         f"(أقل صفقة ممكنة ≈ ${min_notional:.2f} notional)")
        qty = contracts * spec["ctVal"]
        margin = qty * price / config.LEVERAGE
        if margin > self.balance * config.MAX_MARGIN_PCT:
            # قلّص للحد المسموح
            max_qty = self.balance * config.MAX_MARGIN_PCT * config.LEVERAGE / price
            contracts = math.floor(max_qty / spec["ctVal"] / spec["lotSz"]) * spec["lotSz"]
            if contracts < spec["minSz"]:
                return 0.0, "الهامش المطلوب يتجاوز 30% من الرصيد"
            qty = contracts * spec["ctVal"]
        return qty, None

    def open(self, symbol: str, direction: str, price: float, qty: float,
             sl: float, tp: float, atr_val: float, agreement: float) -> Optional[str]:
        fill = price * (1 + config.SLIPPAGE) if direction == "LONG" else price * (1 - config.SLIPPAGE)
        notional = qty * fill
        margin = notional / config.LEVERAGE
        fee = notional * config.TAKER_FEE
        if margin + fee > self.balance:
            log.info(f"❌ [{symbol}] رصيد غير كافٍ للهامش+الرسوم (${margin+fee:.2f})")
            return None
        self.balance -= margin + fee
        self.fees_paid += fee
        pid = f"P{self.next_id}"
        self.next_id += 1
        self.positions[pid] = {
            "symbol": symbol, "dir": direction, "entry": fill, "qty": qty,
            "margin": margin, "sl": sl, "tp": tp, "atr": atr_val,
            "peak": fill, "opened": datetime.now(timezone.utc).isoformat(),
            "agreement": agreement, "breakeven_done": False,
        }
        log.info(f"{'📈' if direction=='LONG' else '📉'} فتح [{symbol}] {direction} "
                 f"@ {fill:.6g} | كمية={qty:.6g} | هامش=${margin:.2f} | "
                 f"SL={sl:.6g} TP={tp:.6g} | إجماع={agreement:.0%}")
        return pid

    def close(self, pid: str, price: float, reason: str) -> Optional[float]:
        p = self.positions.pop(pid, None)
        if not p:
            return None
        fill = price * (1 - config.SLIPPAGE) if p["dir"] == "LONG" else price * (1 + config.SLIPPAGE)
        sign = 1 if p["dir"] == "LONG" else -1
        gross = sign * (fill - p["entry"]) * p["qty"]
        fee = p["qty"] * fill * config.TAKER_FEE
        # التصفية: الخسارة لا تتجاوز الهامش المحجوز (رافعة معزولة)
        pnl = max(gross, -p["margin"]) - fee
        self.balance += p["margin"] + pnl
        self.fees_paid += fee
        trade = {
            "symbol": p["symbol"], "dir": p["dir"], "entry": p["entry"],
            "exit": fill, "qty": p["qty"], "pnl": round(pnl, 4),
            "reason": reason, "opened": p["opened"],
            "closed": datetime.now(timezone.utc).isoformat(),
        }
        self.trades.append(trade)
        emoji = "✅" if pnl > 0 else "🔻"
        log.info(f"{emoji} إغلاق [{p['symbol']}] {p['dir']} @ {fill:.6g} | "
                 f"PnL=${pnl:+.4f} | السبب: {reason}")
        return pnl

    def check_liquidation(self, pid: str, price: float) -> bool:
        """تصفية معزولة تقريبية: خسارة ≥ 90% من الهامش"""
        p = self.positions[pid]
        sign = 1 if p["dir"] == "LONG" else -1
        loss = -sign * (price - p["entry"]) * p["qty"]
        return loss >= p["margin"] * 0.9


# ══════════════════════════════════════════════════════════════════
# 🗄️ قاعدة البيانات — سجل دائم وصادق
# ══════════════════════════════════════════════════════════════════
class Store:
    def __init__(self, path: str = DB_PATH):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS trades(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, dir TEXT, entry REAL, exit_px REAL, qty REAL,
            pnl REAL, reason TEXT, opened TEXT, closed TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS equity(
            ts TEXT, equity REAL, balance REAL, open_positions INTEGER,
            fees_paid REAL)""")
        self.db.commit()

    def save_trade(self, t: dict) -> None:
        self.db.execute(
            "INSERT INTO trades(symbol,dir,entry,exit_px,qty,pnl,reason,opened,closed)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (t["symbol"], t["dir"], t["entry"], t["exit"], t["qty"],
             t["pnl"], t["reason"], t["opened"], t["closed"]))
        self.db.commit()

    def snapshot(self, equity: float, balance: float, n_pos: int, fees: float) -> None:
        self.db.execute("INSERT INTO equity VALUES(?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(),
                         round(equity, 4), round(balance, 4), n_pos, round(fees, 4)))
        self.db.commit()


# ══════════════════════════════════════════════════════════════════
# 🚀 المحرك
# ══════════════════════════════════════════════════════════════════
class Engine:
    def __init__(self, balance: float):
        self.okx = OKXPublic()
        config.SYMBOLS = self.okx.discover_symbols()
        if not config.SYMBOLS:
            raise RuntimeError("لم يتم اكتشاف أي عملة مؤهلة — تحقق من الاتصال")
        self.okx.load_specs(config.SYMBOLS)
        self.broker = PaperBroker(balance, self.okx.specs)
        self.risk = RiskManager(balance)
        self.store = Store()
        self.cycle_n = 0

    def refresh_symbols(self) -> None:
        """تحديث قائمة العملات دورياً — السيولة تتغير على مدار اليوم"""
        fresh = self.okx.discover_symbols()
        if not fresh:
            return  # فشل الجلب؟ نبقى على القائمة الحالية
        held = {p["symbol"] for p in self.broker.positions.values()}
        # لا نُسقط عملة عليها صفقة مفتوحة — تبقى حتى تُغلق صفقتها
        config.SYMBOLS = list(dict.fromkeys(fresh + sorted(held)))
        self.okx.load_specs(config.SYMBOLS)

    # ── إدارة الصفقات المفتوحة ──────────────────────────────────
    def manage_positions(self, prices: Dict[str, float]) -> None:
        for pid in list(self.broker.positions.keys()):
            p = self.broker.positions[pid]
            price = prices.get(p["symbol"])
            if not price:
                continue
            sign = 1 if p["dir"] == "LONG" else -1
            p["peak"] = max(p["peak"], price) if sign == 1 else min(p["peak"], price)

            # Breakeven بعد ربح 1×ATR
            if not p["breakeven_done"]:
                if sign * (price - p["entry"]) >= p["atr"] * config.BREAKEVEN_ATR:
                    p["sl"] = p["entry"]
                    p["breakeven_done"] = True
                    log.info(f"🔒 [{p['symbol']}] SL → نقطة الدخول (Breakeven)")

            # وقف متحرك
            trail = p["peak"] - sign * p["atr"] * config.TRAIL_ATR
            if sign == 1:
                p["sl"] = max(p["sl"], trail) if p["breakeven_done"] else p["sl"]
            else:
                p["sl"] = min(p["sl"], trail) if p["breakeven_done"] else p["sl"]

            reason = None
            if self.broker.check_liquidation(pid, price):
                reason = "تصفية ⚡ (الرافعة أكلت الهامش)"
            elif sign * (price - p["sl"]) <= 0:
                reason = "وقف خسارة 🛑"
            elif sign * (price - p["tp"]) >= 0:
                reason = "هدف ✅"

            if reason:
                pnl = self.broker.close(pid, price, reason)
                if pnl is not None:
                    self.store.save_trade(self.broker.trades[-1])
                    self.risk.record(pnl, self.broker.equity(prices))

    # ── البحث عن صفقات جديدة ────────────────────────────────────
    def scan_for_entries(self, all_candles: Dict[str, List[dict]]) -> None:
        if not self.risk.can_open():
            return
        if len(self.broker.positions) >= config.MAX_POSITIONS:
            return
        held = {p["symbol"] for p in self.broker.positions.values()}
        for symbol, candles in all_candles.items():
            if symbol in held or len(candles) < 120:
                continue
            # استخدم الشموع المؤكدة فقط للإشارة (لا نعيد رسم التاريخ)
            confirmed = [c for c in candles if c["confirmed"]]
            if len(confirmed) < 120:
                continue
            signal, agreement, details = council_vote(confirmed)
            if signal == "NONE":
                continue
            price = candles[-1]["c"]
            a = atr(confirmed)
            if a <= 0:
                continue
            sl_dist = a * config.SL_ATR
            risk_usdt = self.broker.balance * self.risk.risk_pct()
            qty, reject = self.broker.size_position(symbol, price, sl_dist, risk_usdt)
            if reject:
                log.info(f"⚠️  [{symbol}] إشارة {signal} ({agreement:.0%}) لكن الصفقة مرفوضة: {reject}")
                continue
            sign = 1 if signal == "LONG" else -1
            sl = price - sign * sl_dist
            tp = price + sign * a * config.TP_ATR
            voters = ", ".join(f"{k}={v['vote']:+d}" for k, v in details.items() if v["vote"])
            log.info(f"🗳️  [{symbol}] {signal} إجماع={agreement:.0%} ({voters})")
            self.broker.open(symbol, signal, price, qty, sl, tp, a, agreement)
            if len(self.broker.positions) >= config.MAX_POSITIONS:
                break

    # ── التقرير ─────────────────────────────────────────────────
    def report(self, prices: Dict[str, float]) -> None:
        eq = self.broker.equity(prices)
        trades = self.broker.trades
        wins = sum(1 for t in trades if t["pnl"] > 0)
        wr = wins / len(trades) * 100 if trades else 0.0
        pnl_total = sum(t["pnl"] for t in trades)
        log.info("─" * 60)
        log.info(f"❄️  دورة #{self.cycle_n} | رصيد=${self.broker.balance:.4f} | "
                 f"Equity=${eq:.4f} | صفقات مفتوحة={len(self.broker.positions)}")
        log.info(f"   مغلقة={len(trades)} | فوز={wr:.0f}% | PnL=${pnl_total:+.4f} | "
                 f"رسوم مدفوعة=${self.broker.fees_paid:.4f}")
        for p in self.broker.positions.values():
            price = prices.get(p["symbol"], p["entry"])
            sign = 1 if p["dir"] == "LONG" else -1
            upnl = sign * (price - p["entry"]) * p["qty"]
            log.info(f"   ▸ [{p['symbol']}] {p['dir']} @ {p['entry']:.6g} → "
                     f"{price:.6g} | uPnL=${upnl:+.4f}")
        log.info("─" * 60)
        self.store.snapshot(eq, self.broker.balance, len(self.broker.positions),
                            self.broker.fees_paid)

    # ── دورة واحدة ──────────────────────────────────────────────
    def cycle(self) -> None:
        self.cycle_n += 1
        if self.cycle_n > 1 and self.cycle_n % config.SYMBOL_REFRESH_CYCLES == 1:
            self.refresh_symbols()
        all_candles, prices = {}, {}
        for symbol in config.SYMBOLS:
            candles = self.okx.candles(symbol, config.BAR, config.LOOKBACK)
            if candles:
                all_candles[symbol] = candles
                prices[symbol] = candles[-1]["c"]
        if not prices:
            log.warning("لا بيانات من OKX هذه الدورة")
            return
        self.risk.new_day_check(self.broker.equity(prices))
        self.manage_positions(prices)
        self.scan_for_entries(all_candles)
        self.report(prices)

    def run(self, minutes: Optional[float], once: bool) -> None:
        log.info("═" * 60)
        log.info("❄️  SNOWBALL PAPER v1.0 — تداول وهمي على أسعار OKX الحية")
        log.info(f"   رصيد وهمي: ${self.broker.balance:.2f} | رافعة: x{config.LEVERAGE} | "
                 f"مخاطرة: {config.RISK_PCT:.1%}/صفقة")
        log.info("   ⚠️  لا يوجد أي تنفيذ حقيقي — هذا النظام للتعلّم والقياس فقط")
        for s, spec in self.okx.specs.items():
            log.info(f"   {s}: أقل عقد={spec['minSz']} × {spec['ctVal']} "
                     f"(lot={spec['lotSz']})")
        log.info("═" * 60)
        deadline = time.time() + minutes * 60 if minutes else None
        while True:
            start = time.time()
            try:
                self.cycle()
            except Exception as e:
                log.error(f"خطأ في الدورة: {e}", exc_info=True)
            if once or self.risk.halted_forever:
                break
            if deadline and time.time() >= deadline:
                log.info("⏰ انتهت مدة التشغيل المطلوبة")
                break
            time.sleep(max(1.0, config.CYCLE_SECONDS - (time.time() - start)))
        # تقرير نهائي
        trades = self.broker.trades
        pnl = sum(t["pnl"] for t in trades)
        log.info(f"🏁 النهاية: {len(trades)} صفقة | PnL=${pnl:+.4f} | "
                 f"رسوم=${self.broker.fees_paid:.4f} | رصيد=${self.broker.balance:.4f}")


# ══════════════════════════════════════════════════════════════════
# ⏪ المحاكاة التاريخية — إعادة تشغيل الأيام الماضية شمعةً شمعة
# ══════════════════════════════════════════════════════════════════
class Backtester:
    """نفس الوكلاء ونفس الوسيط ونفس المخاطر — على بيانات تاريخية حقيقية.
    فحص SL قبل TP داخل الشمعة الواحدة (الافتراض المتشائم = الأصدق)."""

    def __init__(self, balance: float, days: int):
        self.okx = OKXPublic()
        config.SYMBOLS = self.okx.discover_symbols()
        if not config.SYMBOLS:
            raise RuntimeError("لم يتم اكتشاف عملات")
        self.okx.load_specs(config.SYMBOLS)
        self.broker = PaperBroker(balance, self.okx.specs)
        self.risk = RiskManager(balance)
        self.days = days
        self.data: Dict[str, List[dict]] = {}
        self.rejections: Dict[str, int] = {}
        log.info(f"⏳ تحميل {days} أيام من شموع {config.BAR} لـ {len(config.SYMBOLS)} عملة...")
        for s in config.SYMBOLS:
            candles = self.okx.history_candles(s, config.BAR, days)
            if len(candles) >= 250:
                self.data[s] = candles
                log.info(f"   {s}: {len(candles)} شمعة")
            else:
                log.info(f"   {s}: بيانات غير كافية ({len(candles)}) — استُبعدت")

    def _manage(self, ts: int, bars: Dict[str, dict]) -> None:
        for pid in list(self.broker.positions.keys()):
            p = self.broker.positions[pid]
            bar = bars.get(p["symbol"])
            if not bar:
                continue
            sign = 1 if p["dir"] == "LONG" else -1
            # Breakeven ثم وقف متحرك (بإغلاق الشمعة — تقدير متحفظ)
            best = bar["h"] if sign == 1 else bar["l"]
            p["peak"] = max(p["peak"], best) if sign == 1 else min(p["peak"], best)
            if not p["breakeven_done"] and sign * (best - p["entry"]) >= p["atr"] * config.BREAKEVEN_ATR:
                p["sl"], p["breakeven_done"] = p["entry"], True
            if p["breakeven_done"]:
                trail = p["peak"] - sign * p["atr"] * config.TRAIL_ATR
                p["sl"] = max(p["sl"], trail) if sign == 1 else min(p["sl"], trail)

            reason, exit_px = None, None
            worst = bar["l"] if sign == 1 else bar["h"]
            liq_px = p["entry"] - sign * p["margin"] * 0.9 / p["qty"]
            if sign * (worst - liq_px) <= 0:
                reason, exit_px = "تصفية ⚡", liq_px
            elif sign * (worst - p["sl"]) <= 0:     # SL أولاً — الأصدق
                reason, exit_px = "وقف خسارة 🛑", p["sl"]
            elif sign * ((bar["h"] if sign == 1 else bar["l"]) - p["tp"]) >= 0:
                reason, exit_px = "هدف ✅", p["tp"]
            if reason:
                pnl = self.broker.close(pid, exit_px, reason)
                if pnl is not None:
                    eq = self.broker.equity({s: b["c"] for s, b in bars.items()})
                    self.risk.record(pnl, eq)

    def run(self) -> None:
        # محور زمني موحّد لكل العملات
        all_ts = sorted({c["ts"] for cs in self.data.values() for c in cs})
        index = {s: {c["ts"]: i for i, c in enumerate(cs)} for s, cs in self.data.items()}
        warmup = 200
        log.info(f"▶️  بدء المحاكاة: {len(all_ts)} خطوة زمنية (5 دقائق/خطوة)")
        for step, ts in enumerate(all_ts):
            bars = {s: cs[index[s][ts]] for s, cs in self.data.items() if ts in index[s]}
            if not bars:
                continue
            day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
            self.risk.new_day_check(
                self.broker.equity({s: b["c"] for s, b in bars.items()}), day)
            self._manage(ts, bars)
            # دخول جديد — على الشموع المكتملة فقط وبنفس شروط النسخة الحية
            if not self.risk.can_open() or self.risk.halted_forever:
                if self.risk.halted_forever:
                    break
                continue
            if len(self.broker.positions) >= config.MAX_POSITIONS:
                continue
            held = {p["symbol"] for p in self.broker.positions.values()}
            for s, bar in bars.items():
                if s in held:
                    continue
                i = index[s][ts]
                if i < warmup:
                    continue
                window = self.data[s][i - warmup:i + 1]
                signal, agreement, details = council_vote(window)
                if signal == "NONE":
                    continue
                price = bar["c"]
                a = atr(window)
                if a <= 0:
                    continue
                sl_dist = a * config.SL_ATR
                risk_usdt = self.broker.balance * self.risk.risk_pct()
                qty, reject = self.broker.size_position(s, price, sl_dist, risk_usdt)
                if reject:
                    self.rejections[s] = self.rejections.get(s, 0) + 1
                    continue
                sign = 1 if signal == "LONG" else -1
                self.broker.open(s, signal, price, qty,
                                 price - sign * sl_dist,
                                 price + sign * a * config.TP_ATR, a, agreement)
                if len(self.broker.positions) >= config.MAX_POSITIONS:
                    break
        # إغلاق ما تبقى بسعر آخر شمعة
        last_prices = {s: cs[-1]["c"] for s, cs in self.data.items()}
        for pid in list(self.broker.positions.keys()):
            sym = self.broker.positions[pid]["symbol"]
            self.broker.close(pid, last_prices[sym], "نهاية المحاكاة ⏹")
        self._report()

    def _report(self) -> None:
        t = self.broker.trades
        wins = [x for x in t if x["pnl"] > 0]
        losses = [x for x in t if x["pnl"] <= 0]
        pnl = sum(x["pnl"] for x in t)
        log.info("═" * 60)
        log.info(f"🏁 نتيجة محاكاة {self.days} أيام (بيانات OKX حقيقية):")
        log.info(f"   رأس المال: ${self.risk.start:.2f} → ${self.broker.balance:.4f} "
                 f"({(self.broker.balance/self.risk.start-1)*100:+.2f}%)")
        log.info(f"   صفقات: {len(t)} | فوز: {len(wins)} | خسارة: {len(losses)} "
                 f"| نسبة الفوز: {len(wins)/len(t)*100 if t else 0:.0f}%")
        log.info(f"   صافي PnL: ${pnl:+.4f} | رسوم مدفوعة: ${self.broker.fees_paid:.4f}")
        if wins:
            log.info(f"   متوسط الربح: ${sum(x['pnl'] for x in wins)/len(wins):+.4f}")
        if losses:
            log.info(f"   متوسط الخسارة: ${sum(x['pnl'] for x in losses)/len(losses):+.4f}")
        if self.rejections:
            total_rej = sum(self.rejections.values())
            log.info(f"   ⚠️ إشارات مرفوضة (الرصيد أصغر من حد العقد): {total_rej}")
        if self.risk.halted_forever:
            log.info("   🛑 توقفت المحاكاة مبكراً: تجاوز حد السحب الأقصى")
        log.info("═" * 60)


def main() -> None:
    ap = argparse.ArgumentParser(description="Snowball Paper — تداول وهمي فقط")
    ap.add_argument("--balance", type=float, default=config.PAPER_BALANCE,
                    help="الرصيد الوهمي بالدولار (جرّب 2 لترى واقع حسابك)")
    ap.add_argument("--minutes", type=float, default=None, help="مدة التشغيل بالدقائق")
    ap.add_argument("--once", action="store_true", help="دورة واحدة ثم خروج")
    ap.add_argument("--backtest-days", type=int, default=None,
                    help="محاكاة تاريخية على آخر N أيام بدل التشغيل الحي")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    if args.backtest_days:
        Backtester(args.balance, args.backtest_days).run()
    else:
        Engine(args.balance).run(args.minutes, args.once)


if __name__ == "__main__":
    main()
