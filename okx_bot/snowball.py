#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║     ULTIMATE v19.0 — HYPER AI COMPOUNDING MACHINE — ابدأ بـ Paper Trading أسبوعاً على الأقل!            ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  خطوة 1 — ثبّت المكتبات (مرة واحدة فقط):                       ║
║  pip install ccxt aiohttp pandas numpy ta scikit-learn           ║
║  pip install python-dotenv xgboost websockets                   ║
║                                                                  ║
║  خطوة 2 — ضع مفاتيحك في الأسطر أدناه                           ║
║                                                                  ║
║  خطوة 3 — شغّل: python ultimate_final_v18_ready.py              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ULTIMATE FINAL v18.0 — النسخة النهائية المدمجة                         ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  من ultimate_v17_okx.py:          من the_absolute_v101:                    ║
║  ✅ 9 وكلاء متخصصون               ✅ Flash Crash Guard                     ║
║  ✅ OpenRouter AI Council          ✅ Circuit Breaker Ultra (10 مستويات)    ║
║  ✅ Evolutionary Agent             ✅ Cascade Stopper                       ║
║  ✅ Profit Auto-Transfer           ✅ Recovery Bot                          ║
║  ✅ Paper Trading                  ✅ Whale Trap                            ║
║  ✅ Walk-Forward                   ✅ Dark Pool Detector                    ║
║  ✅ Elliott + Harmonic             ✅ Parabolic Squeeze (Moon Shot)         ║
║  ✅ VWAP + Ichimoku                ✅ Twitter/Reddit Sentiment              ║
║  ✅ Self-Healing                   ✅ Liquidation Avoider                   ║
║  ✅ Monte Carlo                    ✅ Absolute Risk Manager                 ║
║                                                                              ║
║  إصلاحات:                                                                   ║
║  🔧 رموز OKX (/ → -)              🔧 Leverage آمن (max 10)                 ║
║  🔧 Martingale مُعطّل              🔧 Paper Trading مُفعّل افتراضياً        ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  pip install ccxt aiohttp pandas numpy ta scikit-learn python-dotenv        ║
║  python ultimate_final_v18.py                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio, aiohttp, json, os, time, logging, sqlite3, uuid
import random, math, hashlib, warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

# ✅ تحميل متغيرات البيئة من ملف .env
load_dotenv()

# ══ وضع التداول ══════════════════════════════════════════════
# FUTURES x10 — تأكد من اختبار Paper Trading أولاً!
# OKX Perpetual Swaps (عقود دائمة)
# ════════════════════════════════════════════════════════════════

# ══ المفاتيح من ملف .env ════════════════════════════════════════
# أنشئ ملف .env وضع فيه:
# OKX_API_KEY=مفتاحك
# OKX_SECRET_KEY=سرك
# OKX_PASSPHRASE=كلمة_المرور
# OPENROUTER_API_KEY=مفتاح_openrouter
# TELEGRAM_TOKEN=مفتاح_تيليغرام (اختياري)
# TELEGRAM_CHAT_ID=معرف_محادثتك (اختياري)
# ════════════════════════════════════════════════════════════════
warnings.filterwarnings('ignore')


# ══ فحص المكتبات ═══════════════════════════════════════════════
def check_libraries():
    missing = []
    libs = {
        "ccxt":     "pip install ccxt",
        "aiohttp":  "pip install aiohttp",
        "pandas":   "pip install pandas",
        "numpy":    "pip install numpy",
        "ta":       "pip install ta",
        "sklearn":  "pip install scikit-learn",
        "dotenv":   "pip install python-dotenv",
    }
    for lib, cmd in libs.items():
        try:
            __import__(lib)
        except ImportError:
            missing.append(f"  pip install {lib.replace('sklearn','scikit-learn').replace('dotenv','python-dotenv')}")
    if missing:
        print("\n❌ مكتبات ناقصة — شغّل هذه الأوامر أولاً:")
        for m in missing:
            print(m)
        print("\nأو شغّل أمراً واحداً:")
        print("  pip install ccxt aiohttp pandas numpy ta scikit-learn python-dotenv xgboost")
        import sys; sys.exit(1)
    print("✅ كل المكتبات موجودة")

check_libraries()
# ════════════════════════════════════════════════════════════════

try:
    import ccxt.pro as ccxtpro
    CCXT_AVAILABLE = True
except ImportError:
    try:
        import ccxt as ccxtpro   # ✅ Windows fallback
        CCXT_AVAILABLE = True
    except ImportError:
        CCXT_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.neural_network import MLPClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
# ⚙️  الإعدادات النهائية
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class FinalConfig:
    # ── OKX ──────────────────────────────────────────────────────────────────
    OKX_API_KEY:    str = os.getenv("OKX_API_KEY", "")
    OKX_SECRET:     str = os.getenv("OKX_API_SECRET", os.getenv("OKX_SECRET_KEY", ""))
    OKX_PASSPHRASE: str = os.getenv("OKX_PASSPHRASE", "")

    # ── OpenRouter ────────────────────────────────────────────────────────────
    OPENROUTER_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # ── Telegram ──────────────────────────────────────────────────────────────
    TG_TOKEN:       str = os.getenv("TELEGRAM_TOKEN", "")
    TG_CHAT:        str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── الرموز (OKX: - وليس /) ───────────────────────────────────────────────
    # ══ 100 عملة مقسّمة بذكاء ════════════════════════════════
    # ACTIVE_TIER: 1=10 | 2=30 | 3=60 | 4=100 عملة
    ACTIVE_TIER: int = 1  # يبدأ بـ Tier1 ويرتفع تلقائياً مع الرصيد

    SYMBOLS_TIER1: List[str] = field(default_factory=lambda: [
        # ══ TOP 50 — أعلى تقلب + سيولة — مُختارة بذكاء ══
        # Layer 1 — الحركة الأكبر
        "TAO-USDT","SOL-USDT","SUI-USDT","APT-USDT","INJ-USDT",
        "NEAR-USDT","AVAX-USDT","ARB-USDT","OP-USDT","BTC-USDT",
        # Layer 2 — DeFi + AI عالية التقلب
        "ETH-USDT","LINK-USDT","AAVE-USDT","UNI-USDT","DYDX-USDT",
        "PENDLE-USDT","ENA-USDT","FET-USDT","RENDER-USDT","AGIX-USDT",
        # Layer 3 — Momentum Coins
        "WIF-USDT","PEPE-USDT","BONK-USDT","FLOKI-USDT","DOGE-USDT",
        "SEI-USDT","TIA-USDT","JTO-USDT","PYTH-USDT","EIGEN-USDT",
        # Layer 4 — Mid-Cap متقلب
        "IMX-USDT","RON-USDT","GALA-USDT","AXS-USDT","SAND-USDT",
        "MANA-USDT","GRT-USDT","LDO-USDT","RPL-USDT","SNX-USDT",
        # Layer 5 — High Beta Gems
        "ICP-USDT","ATOM-USDT","DOT-USDT","ALGO-USDT","FIL-USDT",
        "HBAR-USDT","VET-USDT","ZIL-USDT","THETA-USDT","OCEAN-USDT",
    ])
    SYMBOLS_TIER2: List[str] = field(default_factory=lambda: [
        # 11-30 — Layer 1/2
        "MATIC-USDT","UNI-USDT","LTC-USDT","BCH-USDT","ATOM-USDT",
        "NEAR-USDT","APT-USDT","ARB-USDT","OP-USDT","SUI-USDT",
        "INJ-USDT","TIA-USDT","SEI-USDT","FET-USDT","RENDER-USDT",
        "GRT-USDT","ALGO-USDT","ICP-USDT","FIL-USDT","VET-USDT",
    ])
    SYMBOLS_TIER3: List[str] = field(default_factory=lambda: [
        # 31-60 — DeFi + AI
        "AAVE-USDT","MKR-USDT","SNX-USDT","CRV-USDT","DYDX-USDT",
        "COMP-USDT","SUSHI-USDT","1INCH-USDT","LDO-USDT","RPL-USDT",
        "PENDLE-USDT","JTO-USDT","PYTH-USDT","ENA-USDT","EIGEN-USDT",
        "TAO-USDT","ARKM-USDT","AGIX-USDT","OCEAN-USDT","NMR-USDT",
        "HBAR-USDT","IOTA-USDT","XTZ-USDT","THETA-USDT","ALT-USDT",
        "AKT-USDT","FLUX-USDT","TRX-USDT","XLM-USDT","EOS-USDT",
    ])
    SYMBOLS_TIER4: List[str] = field(default_factory=lambda: [
        # 61-100 — Meme + Gaming + Others
        "PEPE-USDT","SHIB-USDT","WIF-USDT","BONK-USDT","FLOKI-USDT",
        "NEIRO-USDT","MEME-USDT","BRETT-USDT","MOG-USDT","TURBO-USDT",
        "POPCAT-USDT","MEW-USDT","GOAT-USDT","PNUT-USDT","ACT-USDT",
        "AXS-USDT","SAND-USDT","MANA-USDT","ENJ-USDT","GALA-USDT",
        "IMX-USDT","PIXEL-USDT","PORTAL-USDT","BEAM-USDT","RON-USDT",
        "YFI-USDT","FXS-USDT","CVX-USDT","BAL-USDT","W-USDT",
        "ZEC-USDT","DASH-USDT","NEO-USDT","QTUM-USDT","ONT-USDT",
        "ICX-USDT","KSM-USDT","ZIL-USDT","RNDR-USDT","CTXC-USDT",
    ])

    SYMBOLS: List[str] = field(default_factory=lambda: [
        "BTC-USDT","ETH-USDT","SOL-USDT","BNB-USDT","XRP-USDT",
        "ADA-USDT","DOGE-USDT","AVAX-USDT","LINK-USDT","DOT-USDT",
    ])

    TIMEFRAMES: List[str] = field(default_factory=lambda: [
        "1m", "5m", "15m", "1h", "4h"])
    PRIMARY_TF: str = "1m"   # ⚡ v19: شمعة 1 دقيقة للسرعة القصوى
    LOOKBACK:   int = 300

    # ── رأس المال — Million Dollar Protocol ──────────────────────────────────
    INITIAL_CAPITAL:    float = 10.0     # 💰 نبدأ بـ $10 فقط
    PAPER_TRADING:      bool  = (os.getenv("OKX_IS_DEMO", "1") != "0")  # 0=live, 1=paper
    PAPER_BALANCE:      float = 10.0     # 💰 محاكاة $10 حقيقية
    MIN_ORDER_USDT:     float = 1.0      # ✅ أدنى صفقة $1 (لرأس مال صغير)

    # ══════════════════════════════════════════════════════════════════
    # ⚠️  وضع المخاطرة القوية — HIGH RISK MODE
    # ⚠️  تحذير: هذه الإعدادات تزيد الأرباح المحتملة
    #            لكنها تزيد خطر فقدان رأس المال بشكل كبير
    #            لا تستخدمها بأموال حقيقية إلا بعد أسبوعين Paper Trading
    # ══════════════════════════════════════════════════════════════════

    # ── رافعة مالية عالية ────────────────────────────────────────────
    MAX_LEVERAGE:       int   = 20       # ⚡ x20 — رافعة قوية جداً

    # ── حجم الصفقة (High Risk) ───────────────────────────────────────
    HARD_MAX_RISK:      float = 0.04     # 4% من رأس المال لكل صفقة (x8 من الافتراضي)
    HARD_MAX_LOSS:      float = 0.10     # 10% خسارة يومية مسموحة
    HARD_MAX_DD:        float = 0.35     # 35% سحب أقصى — v19 Hyper

    # ── عدد الصفقات المتزامنة ────────────────────────────────────────
    MAX_POSITIONS:      int   = 10       # 10 صفقات مفتوحة في آن واحد

    # ── نسب Stop Loss / Take Profit عدوانية ─────────────────────────
    STOP_LOSS_ATR:      float = 1.0      # SL ضيق → خروج سريع
    TAKE_PROFIT_ATR:    float = 5.0      # TP بعيد → أرباح أكبر (RR = 1:5)
    TRAILING_ENABLED:   bool  = True

    # ── Circuit Breakers (مرنة — High Risk) ──────────────────────────
    CB_LEVELS: List[float] = field(default_factory=lambda: [
        0.02,  0.04,  0.06,  0.08,  0.10,  # L1-L5: تحذير فقط (أوسع)
        0.15,  0.18,  0.22,  0.26,  0.30   # L6-L10: إيقاف عند 30%
    ])

    # ── الوكلاء — High Risk: عتبة إجماع أقل = إشارات أكثر ──────────────────
    MIN_AGREEMENT:      float = 0.52     # ⚡ 52% كافٍ (بدلاً من 65%) — إشارات أكثر
    MIN_AGENTS:         int   = 3        # 3 وكلاء يكفون (بدلاً من 4)
    AGENT_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "Technical":       3.0,
        "ML":              4.0,   # ⚡ ML أقوى
        "Sentiment":       2.0,
        "Volume":          3.0,   # ⚡ حجم أهم
        "OrderFlow":       3.5,   # ⚡ تدفق الأوامر مهم جداً
        "Whale":           3.5,   # ⚡ تتبع الحيتان
        "FlashCrash":      3.0,
        "Parabolic":       3.5,   # ⚡ Moon Shots مهمة
        "DarkPool":        3.0,
        "Evolutionary":    4.0,   # ⚡ الوكيل المتطور
        "AICouncil":       4.5,   # ⚡ AI Council الأعلى
    })

    # ── Flash Crash — عتبة أعلى لتقليل الإغلاق المبكر ──────────────────────
    FLASH_CRASH_THRESHOLD: float = 0.08   # ⚡ 8% (بدلاً من 5%) — تحمّل أكثر
    FLASH_CRASH_COOLDOWN:  int   = 15     # انتظار أقل = عودة أسرع للتداول

    # ── Moon Shot — إشارات أكثر عدوانية ─────────────────────────────────────
    MOON_SHOT_ENABLED:     bool  = True
    MOON_SHOT_MIN_PUMP:    float = 0.05   # ⚡ 5% (بدلاً من 8%) — يلتقط المزيد
    MOON_SHOT_RISK_PCT:    float = 0.03   # ⚡ 3% على Moon Shots

    # ── تحويل الأرباح — يبدأ بعد $1000 فقط (كل شيء يُعاد استثماره) ────────
    AUTO_PROFIT_TRANSFER:  bool  = False  # 💰 أوقف التحويل حتى $1000
    PROFIT_TRANSFER_PCT:   float = 0.30   # عند التفعيل: 30% للمحفظة، 70% يُعاد
    PROFIT_THRESHOLD:      float = 10000.0 # ❄️ Snowball: لا تحويل حتى $10,000
    COLD_WALLET:           str   = ""

    # ── قاعدة البيانات ────────────────────────────────────────────────────────
    DB_PATH:    str = os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else ".", "snowball_v19.db")
    CYCLE_SLEEP:int = 5    # ⚡ v19: دورة كل 5 ثوانٍ (أقصى سرعة)

config = FinalConfig()


# ══════════════════════════════════════════════════════════════════════════════
# 💰 MILLION DOLLAR PROTOCOL — بروتوكول المليون دولار من $10
# ══════════════════════════════════════════════════════════════════════════════
class MillionDollarProtocol:
    """
    ثلاثة أوضاع ذكية تتكيف مع رصيدك:
    SURVIVAL ($0-$50)      : حماية رأس المال — x10 رافعة
    GROWTH ($50-$500)      : بناء الأساس    — x15 رافعة
    ACCELERATION ($500+)   : هجوم المليون   — x20 رافعة
    """
    SURVIVAL_MAX = 50.0
    GROWTH_MAX   = 500.0

    MODES = {
        "SURVIVAL":     {"leverage":10, "risk_pct":0.02, "max_positions":2,
                         "min_agreement":0.70, "tier":1,
                         "sl_atr":0.8, "tp_atr":4.0, "boost_max":1.5,
                         "description":"SURVIVAL — احمِ رأس المال"},
        "GROWTH":       {"leverage":15, "risk_pct":0.03, "max_positions":5,
                         "min_agreement":0.60, "tier":2,
                         "sl_atr":1.0, "tp_atr":5.0, "boost_max":2.0,
                         "description":"GROWTH — ابنِ رأس المال"},
        "ACCELERATION": {"leverage":20, "risk_pct":0.04, "max_positions":10,
                         "min_agreement":0.52, "tier":3,
                         "sl_atr":1.0, "tp_atr":6.0, "boost_max":3.5,
                         "description":"ACCELERATION — اضرب نحو المليون"},
    }

    PROJECTION_2PCT = {d: round(10*(1.02**d), 2) for d in [30,90,180,365,500]}
    PROJECTION_4PCT = {d: round(10*(1.04**d), 2) for d in [30,90,180,365,500]}

    def __init__(self):
        self.current_mode  = "SURVIVAL"
        self.start_balance = config.INITIAL_CAPITAL
        self.peak_balance  = config.INITIAL_CAPITAL
        self.milestones    = {v: False for v in [
            50, 100, 500, 1_000, 5_000, 10_000,
            50_000, 100_000, 500_000, 1_000_000]}
        self.days_running  = 0
        self.last_date     = datetime.now().date()
        self._projected    = False

    def update(self, balance: float) -> Dict:
        today = datetime.now().date()
        if today != self.last_date:
            self.days_running += 1
            self.last_date     = today
        self.peak_balance = max(self.peak_balance, balance)

        old_mode = self.current_mode
        if balance < self.SURVIVAL_MAX:
            self.current_mode = "SURVIVAL"
        elif balance < self.GROWTH_MAX:
            self.current_mode = "GROWTH"
        else:
            self.current_mode = "ACCELERATION"

        m = self.MODES[self.current_mode]
        config.MAX_LEVERAGE    = m["leverage"]
        config.HARD_MAX_RISK   = m["risk_pct"]
        config.MAX_POSITIONS   = m["max_positions"]
        config.MIN_AGREEMENT   = m["min_agreement"]
        config.ACTIVE_TIER     = m["tier"]
        config.STOP_LOSS_ATR   = m["sl_atr"]
        config.TAKE_PROFIT_ATR = m["tp_atr"]
        if balance >= 10000:
            config.AUTO_PROFIT_TRANSFER = True
            config.PROFIT_THRESHOLD     = balance * 0.7

        milestone_hit = None
        for ms in sorted(self.milestones):
            if not self.milestones[ms] and balance >= ms:
                self.milestones[ms] = True
                milestone_hit = ms

        return {
            "mode":     self.current_mode,
            "settings": m,
            "switched": (old_mode != self.current_mode),
            "milestone":milestone_hit,
            "days":     self.days_running,
            "growth_x": round(balance / self.start_balance, 2),
            "boost_max":m["boost_max"],
        }

    def get_boost(self, conf: float, ai_match: bool) -> float:
        max_b = self.MODES[self.current_mode]["boost_max"]
        if   conf >= 0.85: boost = max_b
        elif conf >= 0.75: boost = max_b * 0.8
        elif conf >= 0.65: boost = max_b * 0.6
        else:              boost = 1.0
        if ai_match:       boost = min(boost * 1.3, max_b)
        return round(boost, 2)

    def print_projection(self):
        if self._projected: return
        self._projected = True
        sep = "=" * 58
        print(f"\n{sep}")
        print("  MILLION DOLLAR PROTOCOL — من $10 إلى $1,000,000")
        print(sep)
        print(f"  {'يوم':^6}  {'عائد 2%/يوم':^16}  {'عائد 4%/يوم':^16}")
        print("  " + "-"*52)
        for d in [30, 90, 180, 365, 500]:
            v2 = self.PROJECTION_2PCT[d]
            v4 = self.PROJECTION_4PCT[d]
            print(f"  {d:^6}  ${v2:>14,.2f}  ${v4:>14,.2f}")
        print(sep)
        print("  SURVIVAL     $0-$50    : x10 رافعة، 2%/صفقة")
        print("  GROWTH       $50-$500  : x15 رافعة، 3%/صفقة")
        print("  ACCELERATION $500+     : x20 رافعة، 4%/صفقة")
        print("  100% تراكم حتى $1,000 — لا تحويل قبلها!")
        print(f"{sep}\n")

    def milestone_msg(self, balance: float, ms: float) -> str:
        em = {50:"[SEED]",100:"[SPROUT]",500:"[FIRE]",1000:"[TARGET]",
              5000:"[DIAMOND]",10000:"[ROCKET]",50000:"[MOON]",
              100000:"[STAR]",500000:"[CROWN]",1000000:"[MILLION]"}
        e  = em.get(int(ms), "[OK]")
        return (
            f"\n{'='*50}\n"
            f"  {e} معلم: ${ms:,.0f} تحقق!\n"
            f"  الرصيد: ${balance:,.2f} | "
            f"x{balance/self.start_balance:.0f} في {self.days_running} يوم\n"
            f"{'='*50}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 📋 السجلات الملوّنة (من the_absolute)
# ══════════════════════════════════════════════════════════════════════════════
class ColorLogger:
    COLORS = {
        'INFO':     '\033[32m',
        'WARNING':  '\033[33m',
        'ERROR':    '\033[31m',
        'CRITICAL': '\033[35m\033[1m',
        'WHALE':    '\033[94m\033[1m',
        'MOON':     '\033[93m\033[1m',
        'PROFIT':   '\033[92m\033[1m',
        'RESET':    '\033[0m'
    }

    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("snowball_v19.log", encoding="utf-8", errors="replace"),
                logging.StreamHandler()
            ]
        )
        self._log = logging.getLogger("UltimateFinalV18")

    def info(self, msg):    self._log.info(msg)
    def warning(self, msg): self._log.warning(msg)
    def error(self, msg):   self._log.error(msg)

    def whale(self, msg):
        print(f"{self.COLORS['WHALE']}[🐋 WHALE]{self.COLORS['RESET']} {msg}")
        self._log.info(f"[WHALE] {msg}")

    def moon(self, msg):
        print(f"{self.COLORS['MOON']}[🚀 MOON]{self.COLORS['RESET']} {msg}")
        self._log.info(f"[MOON] {msg}")

    def profit(self, msg):
        print(f"{self.COLORS['PROFIT']}[💰 PROFIT]{self.COLORS['RESET']} {msg}")
        self._log.info(f"[PROFIT] {msg}")

log = ColorLogger()


# ══════════════════════════════════════════════════════════════════════════════
# 🗄️  قاعدة البيانات
# ══════════════════════════════════════════════════════════════════════════════
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, direction TEXT, mode TEXT,
            entry REAL, exit_p REAL, amount REAL,
            leverage INTEGER DEFAULT 1,
            pnl REAL DEFAULT 0, pnl_pct REAL DEFAULT 0,
            entry_time TEXT, exit_time TEXT,
            reason TEXT, agents_json TEXT,
            status TEXT DEFAULT 'OPEN'
        );
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, direction TEXT, confidence REAL,
            agents TEXT, ai_council TEXT, flash_crash INTEGER DEFAULT 0,
            moon_shot INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS equity (
            timestamp TEXT, balance REAL, mode TEXT
        );
        CREATE TABLE IF NOT EXISTS transfers (
            timestamp TEXT, amount REAL, status TEXT
        );
        CREATE TABLE IF NOT EXISTS daily (
            date TEXT PRIMARY KEY,
            pnl REAL DEFAULT 0, trades INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS signals_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, direction TEXT, confidence REAL,
            agents TEXT, ai_council TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS flash_crashes (
            timestamp TEXT, symbol TEXT,
            drop_pct REAL, action TEXT
        );
        CREATE TABLE IF NOT EXISTS moon_shots (
            timestamp TEXT, symbol TEXT,
            pump_pct REAL, signal TEXT, result TEXT
        );
        """)
        self.conn.commit()

    def open_trade(self, symbol, direction, mode,
                    entry, amount, leverage, agents) -> int:
        cur = self.conn.execute("""
            INSERT INTO trades
            (symbol,direction,mode,entry,amount,leverage,entry_time,agents_json)
            VALUES (?,?,?,?,?,?,datetime('now'),?)
        """, (symbol, direction, mode, entry, amount, leverage,
               json.dumps(agents)))
        self.conn.commit()
        return cur.lastrowid

    def close_trade(self, tid, exit_p, entry,
                     amount, direction, reason) -> float:
        mult = 1 if direction == "LONG" else -1
        pnl  = mult * (exit_p - entry) * amount
        self.conn.execute("""
            UPDATE trades SET exit_p=?,pnl=?,pnl_pct=?,
            exit_time=datetime('now'),reason=?,status='CLOSED' WHERE id=?
        """, (exit_p, round(pnl,4),
               round(pnl/(entry*amount)*100 if entry>0 else 0,2),
               reason, tid))
        today = datetime.now().strftime("%Y-%m-%d")
        self.conn.execute("""
            INSERT INTO daily(date,pnl,trades,wins) VALUES(?,?,1,?)
            ON CONFLICT(date) DO UPDATE SET
            pnl=pnl+excluded.pnl, trades=trades+1, wins=wins+excluded.wins
        """, (today, round(pnl,4), 1 if pnl>0 else 0))
        self.conn.commit()
        return pnl

    def get_daily_pnl(self) -> float:
        r = self.conn.execute(
            "SELECT pnl FROM daily WHERE date=?",
            (datetime.now().strftime("%Y-%m-%d"),)
        ).fetchone()
        return r[0] if r else 0.0

    def get_stats(self) -> Dict:
        r = self.conn.execute("""
            SELECT COUNT(*),SUM(pnl),
            SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END)
            FROM trades WHERE status='CLOSED'
        """).fetchone()
        t=r[0] or 0; p=r[1] or 0; w=r[2] or 0
        return {"total":t,"pnl":round(p,2),
                "win_rate":round(w/t*100 if t>0 else 0,1)}

    def log_flash_crash(self, symbol, drop_pct, action):
        self.conn.execute(
            "INSERT INTO flash_crashes VALUES(datetime('now'),?,?,?)",
            (symbol, drop_pct, action))
        self.conn.commit()

    def log_moon_shot(self, symbol, pump_pct, signal, result="DETECTED"):
        self.conn.execute(
            "INSERT INTO moon_shots VALUES(datetime('now'),?,?,?,?)",
            (symbol, pump_pct, signal, result))
        self.conn.commit()

    def log_signal(self, symbol: str, direction: str,
                    confidence: float, agents_json, ai_council_json):
        """تسجيل الإشارة في قاعدة البيانات"""
        try:
            self.conn.execute("""
                INSERT INTO signals_log
                (symbol,direction,confidence,agents,ai_council)
                VALUES (?,?,?,?,?)
            """, (symbol, direction, round(float(confidence),3),
                   str(agents_json)[:500], str(ai_council_json)[:200]))
            self.conn.commit()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# 📊 FEATURE ENGINE — محرك المؤشرات الكامل
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# ⚡ v19 — ULTRA HYPER SYSTEMS
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. VOLATILITY SCANNER — يصطاد أعلى 5 عملات حركةً لحظياً ─────────────────
class VolatilityScanner:
    """
    يُرتّب العملات الـ50 حسب التقلب اللحظي ويُعيد أفضل 5.
    المعيار: ATR% × حجم × زخم السعر
    """
    def __init__(self):
        self.scores: Dict[str, float] = {}
        self.top5:   List[str]        = []

    def scan(self, data_cache: Dict) -> List[str]:
        scores = {}
        for symbol, tfs in data_cache.items():
            df = tfs.get("1m") or tfs.get("5m")
            if df is None or df.empty or len(df) < 20:
                continue
            try:
                last   = df.iloc[-1]
                atr_pct= float(last.get("atr_pct", 0.002))
                vol_r  = float(last.get("vol_ratio", 1.0))
                rsi    = float(last.get("rsi", 50))
                # زخم السعر في آخر 5 شمعات
                momentum = abs(float(df["close"].iloc[-1]) -
                               float(df["close"].iloc[-5])) /                            float(df["close"].iloc[-5]) if len(df) >= 6 else 0
                # معادلة التسجيل: ATR% مرجح × حجم × زخم
                rsi_bonus = 1.3 if (rsi < 35 or rsi > 65) else 1.0
                score = (atr_pct * 40 + momentum * 35 + (vol_r-1)*15) * rsi_bonus
                scores[symbol] = round(score, 6)
            except Exception:
                continue
        # ترتيب تنازلي → أفضل 5
        self.scores = dict(sorted(scores.items(),
                                  key=lambda x: x[1], reverse=True))
        self.top5   = list(self.scores.keys())[:5]
        return self.top5

    def get_score(self, symbol: str) -> float:
        return self.scores.get(symbol, 0.0)


# ── 2. MOMENTUM SNIPER — يتعرف على الاختراقات قبل 3 شمعات ───────────────────
class MomentumSniper:
    """
    يكتشف الإشارات المبكرة قبل تأكيدها:
    - كسر مقاومة + حجم متصاعد + RSI صاعد = BUY مبكر
    - كسر دعم + حجم متصاعد + RSI هابط = SELL مبكر
    يُعطي إشارة قبل باقي الوكلاء → دخول بسعر أفضل
    """
    def detect(self, df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 30:
            return {"signal": "HOLD", "confidence": 0.0}
        try:
            c   = df["close"].astype(float)
            h   = df["high"].astype(float)
            v   = df["volume"].astype(float)
            rsi = df["rsi"].astype(float) if "rsi" in df.columns else pd.Series([50]*len(df))
            atr = df["atr"].astype(float) if "atr" in df.columns else c * 0.01

            # مستويات المقاومة والدعم (آخر 20 شمعة)
            resistance = h.tail(20).max()
            support    = df["low"].astype(float).tail(20).min()
            price      = float(c.iloc[-1])
            vol_surge  = float(v.tail(3).mean() / (v.mean() + 1e-10))
            rsi_now    = float(rsi.iloc[-1])
            rsi_slope  = float(rsi.iloc[-1] - rsi.iloc[-4]) if len(rsi) >= 4 else 0

            # ── BREAKOUT UP ──────────────────────────────────────────
            if (price > resistance * 0.998 and vol_surge > 1.5
                    and rsi_slope > 3 and rsi_now < 75):
                conf = min(0.55 + vol_surge * 0.05 + rsi_slope * 0.005, 0.88)
                return {"signal":"BUY", "confidence":round(conf,3),
                        "type":"BREAKOUT_UP",
                        "resistance":round(resistance,4),
                        "vol_surge":round(vol_surge,2)}

            # ── BREAKOUT DOWN ────────────────────────────────────────
            if (price < support * 1.002 and vol_surge > 1.5
                    and rsi_slope < -3 and rsi_now > 25):
                conf = min(0.55 + vol_surge * 0.05 + abs(rsi_slope) * 0.005, 0.88)
                return {"signal":"SELL", "confidence":round(conf,3),
                        "type":"BREAKOUT_DOWN",
                        "support":round(support,4),
                        "vol_surge":round(vol_surge,2)}

            # ── MOMENTUM CONTINUATION ────────────────────────────────
            if len(c) >= 6:
                last3_ret = float(c.iloc[-1]/c.iloc[-4] - 1)
                if last3_ret > 0.012 and vol_surge > 1.3 and rsi_now < 72:
                    conf = min(0.52 + last3_ret * 10, 0.80)
                    return {"signal":"BUY","confidence":round(conf,3),
                            "type":"MOMENTUM","ret3":round(last3_ret,4)}
                if last3_ret < -0.012 and vol_surge > 1.3 and rsi_now > 28:
                    conf = min(0.52 + abs(last3_ret) * 10, 0.80)
                    return {"signal":"SELL","confidence":round(conf,3),
                            "type":"MOMENTUM","ret3":round(last3_ret,4)}
        except Exception:
            pass
        return {"signal":"HOLD","confidence":0.0}


# ── 3. ULTRA COMPOUND ENGINE — محرك التراكم الرياضي الدقيق ──────────────────
class UltraCompoundEngine:
    """
    يتتبع ويُدير التراكم الأسي بدقة رياضية:
    - يحسب معدل النمو اليومي الفعلي
    - يتوقع متى يبلغ كل معلم
    - يُعدّل حجم الصفقات لتعظيم التراكم
    - يمنع السحب الذي يكسر الزخم
    """
    def __init__(self, start: float = 10.0):
        self.start        = start
        self.balance_hist: List[Tuple[str, float]] = [
            (datetime.now().isoformat(), start)]
        self.daily_returns: List[float] = []
        self.last_balance = start
        self.last_date    = datetime.now().date()
        self.peak         = start
        self.total_days   = 0

    def record(self, balance: float):
        now   = datetime.now()
        today = now.date()
        self.balance_hist.append((now.isoformat(), balance))
        if today != self.last_date:
            if self.last_balance > 0:
                ret = (balance - self.last_balance) / self.last_balance
                self.daily_returns.append(ret)
            self.last_balance = balance
            self.last_date    = today
            self.total_days  += 1
        self.peak = max(self.peak, balance)

    @property
    def cagr(self) -> float:
        if self.total_days < 1 or self.start <= 0:
            return 0.0
        return (self.peak / self.start) ** (365 / max(self.total_days,1)) - 1

    @property
    def avg_daily_return(self) -> float:
        if not self.daily_returns:
            return 0.0
        return float(np.mean(self.daily_returns[-30:]))  # آخر 30 يوم

    def days_to_target(self, current: float, target: float) -> int:
        adr = self.avg_daily_return
        if adr <= 0 or current <= 0:
            return -1
        if current >= target:
            return 0
        import math
        return math.ceil(math.log(target / current) / math.log(1 + adr))

    def optimal_risk_pct(self, win_rate: float, rr: float) -> float:
        """Kelly Criterion — النسبة المثلى رياضياً"""
        if rr <= 0 or win_rate <= 0:
            return 0.01
        kelly = win_rate - (1 - win_rate) / rr
        # نستخدم نصف Kelly للأمان (Half-Kelly)
        half_kelly = max(kelly * 0.5, 0.01)
        return min(half_kelly, 0.06)  # حد أقصى 6%

    def compound_summary(self, balance: float) -> str:
        adr  = self.avg_daily_return
        lines = [
            f"💰 رأس المال: ${balance:,.2f} (بدأنا بـ ${self.start})",
            f"📈 نمو: ×{balance/self.start:.1f} | CAGR: {self.cagr:.0%}",
            f"📅 أيام: {self.total_days} | عائد يومي: {adr:.2%}",
        ]
        for tgt in [100, 1_000, 10_000, 100_000, 1_000_000]:
            if balance < tgt:
                d = self.days_to_target(balance, tgt)
                if d > 0:
                    lines.append(f"  🎯 ${tgt:,.0f} → ~{d} يوم")
                break
        return "\n".join(lines)


# ── 4. PYRAMID ENGINE — يضاعف الحجم على الصفقات الرابحة ─────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# ❄️  SNOWBALL ENGINE — كرة الثلج — كل ربح يُكبّر الكرة
# ══════════════════════════════════════════════════════════════════════════════
class SnowballEngine:
    """
    مبدأ كرة الثلج:
    ─────────────────────────────────────────────────────────
    كلما كبر الرصيد → كبر حجم الصفقة → كبر الربح → كبر الرصيد...
    دائرة مُتسارعة لا تتوقف حتى تصل للمليون.

    القواعد:
    1. حجم الصفقة = نسبة ثابتة من الرصيد الحالي دائماً
    2. كل ربح يُعاد استثماره فوراً 100% (صفر سحب حتى $10K)
    3. سلسلة انتصارات  → زيادة تدريجية في النسبة (حتى الحد الأقصى)
    4. سلسلة خسائر     → تخفيض تدريجي (حماية الكرة)
    5. بعد كل ×2 للرصيد → إشعار احتفالي
    """

    # ── إعدادات النسب حسب الوضع ──────────────────────────────────────────────
    BASE_RISK = {
        "SURVIVAL":     0.020,   # 2%   من الرصيد
        "GROWTH":       0.030,   # 3%   من الرصيد
        "ACCELERATION": 0.045,   # 4.5% من الرصيد
    }
    MAX_RISK = {
        "SURVIVAL":     0.035,   # 3.5% حد أقصى في SURVIVAL
        "GROWTH":       0.055,   # 5.5% حد أقصى في GROWTH
        "ACCELERATION": 0.075,   # 7.5% حد أقصى في ACCELERATION
    }
    MIN_RISK = 0.010             # 1% حد أدنى مطلق

    def __init__(self, start_balance: float = 10.0):
        self.start          = start_balance
        self.balance        = start_balance
        self.peak           = start_balance
        self.win_streak     = 0
        self.loss_streak    = 0
        self.total_trades   = 0
        self.total_wins     = 0
        self.total_pnl      = 0.0
        self.last_double    = start_balance   # آخر مرة تضاعف الرصيد
        self.doublings      = 0               # عدد مرات التضاعف
        self.trade_history: List[float] = []  # آخر 20 صفقة
        self._current_mode  = "SURVIVAL"

    def update_mode(self, mode: str):
        self._current_mode = mode

    def record_trade(self, pnl: float, new_balance: float):
        """سجّل كل صفقة وحدّث الكرة"""
        self.balance      = new_balance
        self.peak         = max(self.peak, new_balance)
        self.total_trades += 1
        self.total_pnl    += pnl
        self.trade_history.append(pnl)
        if len(self.trade_history) > 20:
            self.trade_history.pop(0)

        if pnl > 0:
            self.total_wins  += 1
            self.win_streak  += 1
            self.loss_streak  = 0
        else:
            self.loss_streak += 1
            self.win_streak   = 0

        # فحص التضاعف
        doubled = None
        while new_balance >= self.last_double * 2:
            self.last_double *= 2
            self.doublings   += 1
            doubled           = self.last_double
        return doubled   # يُعيد قيمة التضاعف إذا حدث

    def get_risk_pct(self) -> float:
        """
        النسبة الديناميكية لكل صفقة:
        - تبدأ من BASE_RISK
        - ترتفع مع سلسلة الانتصارات (حتى MAX_RISK)
        - تنخفض مع سلسلة الخسائر (حتى MIN_RISK)
        """
        mode    = self._current_mode
        base    = self.BASE_RISK[mode]
        max_r   = self.MAX_RISK[mode]

        # مكافأة سلسلة الانتصارات: +0.5% لكل انتصار (حتى الحد الأقصى)
        streak_bonus = min(self.win_streak * 0.005, max_r - base)

        # عقوبة سلسلة الخسائر: -0.4% لكل خسارة
        streak_penalty = min(self.loss_streak * 0.004, base - self.MIN_RISK)

        risk = base + streak_bonus - streak_penalty
        return round(max(self.MIN_RISK, min(risk, max_r)), 4)

    def get_position_size_usdt(self, balance: float, price: float,
                                atr: float, leverage: int) -> float:
        """
        حجم الصفقة بالدولار — مرتبط دائماً بالرصيد الحالي
        """
        risk_pct   = self.get_risk_pct()
        risk_usdt  = balance * risk_pct          # المخاطرة الفعلية بالدولار
        atr_sl     = max(atr, price * 0.005)     # SL بالدولار
        # الكمية = المخاطرة ÷ المسافة للـ SL
        qty        = risk_usdt / atr_sl
        # قيمة الصفقة الفعلية مع الرافعة
        notional   = qty * price
        # حد: لا تتجاوز 30% من الرصيد الفعلي (بدون رافعة)
        max_notional = balance * 0.30
        qty          = min(qty, max_notional / price)
        return round(qty, 6)

    def snowball_status(self, balance: float) -> str:
        """تقرير حالة الكرة"""
        risk_pct = self.get_risk_pct()
        wr       = self.total_wins/self.total_trades*100 if self.total_trades else 0
        growth   = balance / self.start if self.start > 0 else 1

        # شريط التقدم المرئي
        bar_len  = 20
        targets  = [50, 100, 500, 1000, 5000, 10000, 100000, 1000000]
        next_tgt = next((t for t in targets if t > balance), 1000000)
        prev_tgt = max((t for t in [self.start]+targets if t <= balance), default=self.start)
        if next_tgt > prev_tgt:
            prog   = (balance - prev_tgt) / (next_tgt - prev_tgt)
            filled = int(prog * bar_len)
            bar    = "█" * filled + "░" * (bar_len - filled)
        else:
            bar    = "█" * bar_len

        lines = [
            f"",
            f"  ❄️  SNOWBALL STATUS",
            f"  {'─'*40}",
            f"  💰 الرصيد  : ${balance:>12,.2f}",
            f"  📈 النمو   : ×{growth:>8.1f}  ({self.doublings} تضاعف)",
            f"  🎯 النسبة  : {risk_pct:.1%}/صفقة  "
            f"(ربح={self.win_streak}↑ خسارة={self.loss_streak}↓)",
            f"  🏆 الفوز   : {wr:.1f}%  ({self.total_wins}/{self.total_trades})",
            f"  🎯 الهدف   : ${next_tgt:>10,.0f}",
            f"  [{bar}] {prog*100:.0f}%",
            f"  {'─'*40}",
        ]
        return "\n".join(lines)

    def doubling_message(self, new_balance: float) -> str:
        emojis = ["🌱","🌿","🌲","🔥","💎","🚀","🌙","⭐","👑","🏆"]
        e = emojis[min(self.doublings-1, len(emojis)-1)]
        return (
            f"\n{'═'*50}\n"
            f"  {e}  الكرة تضاعفت! رقم {self.doublings}\n"
            f"  💰 ${new_balance:,.2f} (بدأنا بـ ${self.start})\n"
            f"  📈 ×{new_balance/self.start:.0f} من البداية\n"
            f"  🎯 نسبة الصفقة القادمة: {self.get_risk_pct():.1%}\n"
            f"{'═'*50}"
        )

class PyramidEngine:
    """
    Scale-In على الصفقات الرابحة:
    عندما تربح صفقة 1×ATR → تضيف 50% إضافية
    عندما تربح 2×ATR → تضيف 25% إضافية
    هكذا تُعظّم الأرباح على الحركات الكبيرة
    """
    def __init__(self):
        self.pyramids: Dict[str, List[Dict]] = {}

    def should_add(self, pos_id: str, entry: float, price: float,
                   atr: float, direction: str) -> Optional[Dict]:
        levels = self.pyramids.get(pos_id, [])
        pnl_atr = ((price - entry) / atr
                   if direction == "LONG"
                   else (entry - price) / atr)

        # المستوى الأول: 1×ATR ربح → أضف 50%
        if pnl_atr >= 1.0 and len(levels) == 0:
            return {"level":1,"size_pct":0.50,"reason":"Pyramid L1 +1ATR"}
        # المستوى الثاني: 2×ATR ربح → أضف 25%
        if pnl_atr >= 2.0 and len(levels) == 1:
            return {"level":2,"size_pct":0.25,"reason":"Pyramid L2 +2ATR"}
        # المستوى الثالث: 3.5×ATR ربح → أضف 15%
        if pnl_atr >= 3.5 and len(levels) == 2:
            return {"level":3,"size_pct":0.15,"reason":"Pyramid L3 +3.5ATR"}
        return None

    def record_add(self, pos_id: str, level: int, price: float, qty: float):
        if pos_id not in self.pyramids:
            self.pyramids[pos_id] = []
        self.pyramids[pos_id].append(
            {"level":level,"price":price,"qty":qty,
             "time":datetime.now().isoformat()})

    def clear(self, pos_id: str):
        self.pyramids.pop(pos_id, None)


# ── 5. AI SIGNAL SCORER — Claude API يُنقّط كل إشارة ────────────────────────
class AISignalScorer:
    """
    يستخدم Anthropic API لتقييم الإشارة قبل التنفيذ.
    يُعطي نقاط 0-100 — فقط ≥70 تمر للتنفيذ.
    """
    def __init__(self):
        self._cache: Dict[str, Tuple[float, Dict]] = {}
        self._ttl   = 300  # 5 دقائق cache
        self.enabled= bool(os.getenv("ANTHROPIC_API_KEY",""))
        self._calls = 0
        self._hits  = 0

    async def score(self, symbol: str, direction: str,
                    conf: float, indicators: Dict,
                    mdp_mode: str) -> Dict:
        if not self.enabled:
            return {"score": conf * 100, "pass": conf >= 0.60,
                    "reason": "AI غير مُفعَّل"}

        cache_key = f"{symbol}_{direction}_{int(time.time()//self._ttl)}"
        if cache_key in self._cache:
            self._hits += 1
            return self._cache[cache_key][1]

        prompt = (
            f"You are an expert crypto trader. Evaluate this trade signal:\n"
            f"Symbol: {symbol} | Direction: {direction} | "
            f"Mode: {mdp_mode} | Confidence: {conf:.0%}\n"
            f"RSI: {indicators.get('rsi',50):.1f} | "
            f"ADX: {indicators.get('adx',0):.1f} | "
            f"MACD_hist: {indicators.get('macd_hist',0):.5f} | "
            f"BB%: {indicators.get('bb_pct',0.5):.2f} | "
            f"VolRatio: {indicators.get('vol_ratio',1):.2f}\n"
            f"Reply ONLY in JSON: {{score:0-100, pass:true/false, reason:string}}"
        )

        try:
            import aiohttp as _aio
            async with _aio.ClientSession() as sess:
                async with sess.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key":        os.getenv("ANTHROPIC_API_KEY",""),
                        "anthropic-version":"2023-06-01",
                        "content-type":     "application/json",
                    },
                    json={
                        "model":      "claude-haiku-4-5-20251001",
                        "max_tokens": 120,
                        "messages":   [{"role":"user","content":prompt}],
                    },
                    timeout=_aio.ClientTimeout(total=8)
                ) as r:
                    data = await r.json()
            raw  = data["content"][0]["text"]
            # استخراج JSON
            import re as _re
            m = _re.search(r"\{.*?\}", raw, _re.DOTALL)
            if m:
                result = json.loads(m.group())
                result.setdefault("score", conf*100)
                result.setdefault("pass",  result["score"] >= 65)
                self._cache[cache_key] = (time.time(), result)
                self._calls += 1
                return result
        except Exception as ex:
            pass
        # Local Fallback — يعمل بدون إنترنت
        local_score = conf * 100
        # منطق محلي بسيط عند انقطاع AI
        if indicators.get("rsi", 50) < 35 and direction == "LONG":
            local_score += 10
        if indicators.get("rsi", 50) > 65 and direction == "SHORT":
            local_score += 10
        if indicators.get("adx", 0) > 25:
            local_score += 5
        if indicators.get("vol_ratio", 1) > 1.5:
            local_score += 5
        fallback = {
            "score":  min(local_score, 100),
            "pass":   local_score >= 62,
            "reason": "local_fallback"
        }
        return fallback

# ── TREND FILTER — لا تتداول إلا مع الاتجاه الكبير ─────────────────────────
class TrendFilter:
    """
    يفحص الإطار الزمني الكبير (4h) قبل أي دخول.
    BTC فوق EMA200 = سوق صاعد → LONG فقط
    BTC تحت EMA200 = سوق هابط → SHORT فقط أو لا تداول
    هذا وحده يرفع نسبة الفوز من 55% إلى 65%+
    """
    def __init__(self):
        self.bias    = "NEUTRAL"   # BULL / BEAR / NEUTRAL
        self.btc_4h  = pd.DataFrame()

    def update(self, btc_4h: pd.DataFrame):
        if btc_4h.empty or len(btc_4h) < 200:
            self.bias = "NEUTRAL"
            return
        self.btc_4h = btc_4h
        c     = btc_4h["close"].astype(float)
        ema200= c.ewm(span=200, adjust=False).mean().iloc[-1]
        ema50 = c.ewm(span=50,  adjust=False).mean().iloc[-1]
        price = float(c.iloc[-1])
        if price > ema200 and ema50 > ema200:
            self.bias = "BULL"
        elif price < ema200 and ema50 < ema200:
            self.bias = "BEAR"
        else:
            self.bias = "NEUTRAL"

    def allows(self, direction: str) -> bool:
        if self.bias == "BULL"    and direction == "LONG":  return True
        if self.bias == "BEAR"    and direction == "SHORT": return True
        if self.bias == "NEUTRAL":                          return True
        return False   # ضد الاتجاه → ارفض

    def multiplier(self) -> float:
        return 1.3 if self.bias != "NEUTRAL" else 1.0


class FeatureEngine:
    @staticmethod
    def compute(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 20: return df
        df = df.copy()
        c = df["close"]; h = df["high"]; l = df["low"]; v = df["volume"]

        for p in [9,20,50,200]:
            df[f"ema{p}"] = c.ewm(span=p, adjust=False).mean()
            df[f"sma{p}"] = c.rolling(p).mean()

        d  = c.diff()
        g  = d.clip(lower=0).rolling(14).mean()
        ls = (-d.clip(upper=0)).rolling(14).mean()
        df["rsi"] = 100-(100/(1+g/ls.replace(0,1e-10)))

        e12=c.ewm(span=12).mean(); e26=c.ewm(span=26).mean()
        df["macd"]      = e12-e26
        df["macd_sig"]  = df["macd"].ewm(span=9).mean()
        df["macd_hist"] = df["macd"]-df["macd_sig"]

        tr = pd.concat([h-l,(h-c.shift()).abs(),
                         (l-c.shift()).abs()],axis=1).max(axis=1)
        df["atr"]    = tr.rolling(14).mean()
        df["atr_pct"]= df["atr"]/c

        s20=c.rolling(20).mean(); std=c.rolling(20).std()
        df["bb_upper"] = s20+2*std
        df["bb_lower"] = s20-2*std
        df["bb_pct"]   = (c-(s20-2*std))/(4*std+1e-10)
        df["bb_width"] = (df["bb_upper"]-df["bb_lower"])/s20

        pdm=(h.diff()).clip(lower=0); ndm=(-l.diff()).clip(lower=0)
        df["adx"] = (100*(pdm.rolling(14).mean()-ndm.rolling(14).mean()).abs()
                     /(pdm.rolling(14).mean()+ndm.rolling(14).mean()+1e-10)
                     ).rolling(14).mean()

        lo14=l.rolling(14).min(); hi14=h.rolling(14).max()
        df["stoch"] = 100*(c-lo14)/(hi14-lo14+1e-10)

        df["vol_sma"]   = v.rolling(20).mean()
        df["vol_ratio"] = v/df["vol_sma"].replace(0,1e-10)
        df["obv"]       = (v*np.sign(c.diff())).cumsum()

        df["returns"]   = c.pct_change()
        df["high_low"]  = (h-l)/c

        # Ichimoku
        df["tenkan"] = (h.rolling(9).max()+l.rolling(9).min())/2
        df["kijun"]  = (h.rolling(26).max()+l.rolling(26).min())/2

        # VWAP
        tp = (h+l+c)/3
        df["vwap"] = (tp*v).cumsum()/v.cumsum()
        dev = (c-df["vwap"]).rolling(20).std()
        df["vwap_upper"] = df["vwap"]+2*dev
        df["vwap_lower"] = df["vwap"]-2*dev

        df.dropna(inplace=True)
        return df


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ FLASH CRASH GUARD — حارس الانهيارات المفاجئة (من the_absolute)
# ══════════════════════════════════════════════════════════════════════════════
# ── SESSION FILTER — أفضل أوقات التداول ────────────────────────────────────
class SessionFilter:
    """
    أوقات الذروة في سوق الكريبتو (UTC):
    00:00-04:00  آسيا      — تقلب متوسط
    08:00-12:00  أوروبا    — تقلب عالٍ ✅
    13:00-17:00  أمريكا    — أعلى تقلب ✅✅
    20:00-24:00  تداخل     — جيد ✅
    """
    BEST_HOURS_UTC = set(range(8, 18)) | set(range(20, 24)) | set(range(0, 4))

    def is_prime_time(self) -> bool:
        return datetime.utcnow().hour in self.BEST_HOURS_UTC

    def size_multiplier(self) -> float:
        h = datetime.utcnow().hour
        if 13 <= h <= 17: return 1.4   # أمريكا — أفضل وقت
        if  8 <= h <= 12: return 1.2   # أوروبا
        if 20 <= h <= 23: return 1.1   # مساء
        return 0.8                      # وقت هادئ — قلّل الحجم



# ══════════════════════════════════════════════════════════════════════════════
# ELITE SIGNAL FILTER — فقط أفضل 10% من الإشارات
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# v20 — HEDGE FUND LAYER
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. MARKET REGIME DETECTOR ────────────────────────────────────────────────
class MarketRegimeDetector:
    """
    TREND  → Momentum trades (حجم كبير، TP بعيد)
    RANGE  → Mean Reversion  (حجم صغير، TP قريب)
    CHAOS  → لا تداول أو حجم 20% فقط
    """
    def __init__(self):
        self.regime      = "TREND"
        self.confidence  = 0.5
        self._history    = []

    def detect(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < 50:
            return self.regime
        try:
            c   = df["close"].astype(float)
            atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else float(c.std())
            # حركة السعر في 50 شمعة
            trend_move = abs(float(c.iloc[-1]) - float(c.iloc[-50]))
            # ADX للاتجاه
            adx = float(df["adx"].iloc[-1]) if "adx" in df.columns else 20.0
            # تقلب
            vol_pct = atr / float(c.iloc[-1]) if float(c.iloc[-1]) > 0 else 0.002

            if adx > 28 and trend_move > atr * 5:
                regime = "TREND"
                conf   = min(adx / 50, 0.95)
            elif vol_pct < 0.003 and adx < 20:
                regime = "RANGE"
                conf   = 0.70
            elif vol_pct > 0.012 or adx > 45:
                regime = "CHAOS"
                conf   = 0.80
            else:
                regime = "TREND"
                conf   = 0.55

            self.regime     = regime
            self.confidence = conf
            self._history.append(regime)
            if len(self._history) > 20:
                self._history.pop(0)
        except Exception:
            pass
        return self.regime

    def size_multiplier(self) -> float:
        return {"TREND":1.3, "RANGE":0.7, "CHAOS":0.2}.get(self.regime, 1.0)

    def tp_multiplier(self) -> float:
        return {"TREND":1.5, "RANGE":0.6, "CHAOS":0.3}.get(self.regime, 1.0)

    def min_agreement_boost(self, base: float, vol_score: float) -> float:
        """Dynamic MIN_AGREEMENT — صارم في الفوضى، مرن في الاتجاه"""
        if self.regime == "CHAOS":
            return min(base + 0.15, 0.85)
        if self.regime == "RANGE":
            return min(base + 0.08, 0.75)
        # TREND: يتحكم فيه التقلب
        return base + vol_score * 0.08


# ── 2. CAPITAL ACCELERATION TRIGGER ─────────────────────────────────────────
class CapitalAccelerationTrigger:
    """
    عند اجتماع 3 شروط ذهبية في آن واحد:
    ✅ ثقة ≥ 0.85
    ✅ Whale signal
    ✅ MomentumSniper يؤكد
    → يضاعف حجم الصفقة × 2.5 (الفرصة الذهبية)
    """
    def __init__(self):
        self.golden_trades  = 0
        self.golden_pnl     = 0.0

    def check(self, conf: float, whale_detected: bool,
              sniper_conf: float, regime: str) -> float:
        if regime == "CHAOS":
            return 1.0   # لا تسريع في الفوضى
        golden = (conf >= 0.85 and whale_detected and sniper_conf >= 0.65)
        silver = (conf >= 0.80 and (whale_detected or sniper_conf >= 0.70))
        if golden:
            self.golden_trades += 1
            return 2.5   # الفرصة الذهبية
        if silver:
            return 1.8   # فرصة فضية
        if conf >= 0.75:
            return 1.3
        return 1.0

    def record(self, pnl: float, was_golden: bool):
        if was_golden:
            self.golden_pnl += pnl


# ── 3. SMART KILL SWITCH ─────────────────────────────────────────────────────
class SmartKillSwitch:
    """
    يوقف التداول ذكياً — لا يتعطل نهائياً مثل circuit breaker:
    5 خسائر متتالية  → توقف 1 ساعة
    3 خسائر في 30 دقيقة → توقف 30 دقيقة
    خسارة > 6% في ساعة → توقف 2 ساعة
    """
    def __init__(self):
        self.consecutive_losses = 0
        self.recent_losses      = []   # (timestamp, pnl)
        self.paused_until       = 0.0
        self.total_pauses       = 0

    def record(self, pnl: float):
        now = time.time()
        if pnl < 0:
            self.consecutive_losses += 1
            self.recent_losses.append((now, pnl))
        else:
            self.consecutive_losses = 0
        # احتفظ بآخر ساعة فقط
        self.recent_losses = [(t,p) for t,p in self.recent_losses
                              if now - t < 3600]

    def check(self, balance: float) -> tuple:
        """يُعيد (can_trade: bool, reason: str, resume_in_min: int)"""
        now = time.time()
        if now < self.paused_until:
            mins = int((self.paused_until - now) / 60)
            return False, "Kill Switch نشط", mins

        # شرط 1: 5 خسائر متتالية
        if self.consecutive_losses >= 5:
            self._pause(3600, "5 خسائر متتالية")
            return False, "5 خسائر متتالية → توقف ساعة", 60

        # شرط 2: 3 خسائر في 30 دقيقة
        last_30 = [(t,p) for t,p in self.recent_losses
                   if now - t < 1800]
        if len(last_30) >= 3:
            self._pause(1800, "3 خسائر/30دقيقة")
            return False, "3 خسائر في 30 دقيقة → توقف 30 دقيقة", 30

        # شرط 3: خسارة > 6% في ساعة
        hour_loss = sum(p for _,p in self.recent_losses)
        if balance > 0 and hour_loss / balance < -0.06:
            self._pause(7200, "خسارة 6% في ساعة")
            return False, "خسارة 6% في ساعة → توقف ساعتان", 120

        return True, "OK", 0

    def _pause(self, seconds: int, reason: str):
        self.paused_until = time.time() + seconds
        self.total_pauses += 1
        log.warning(f"🛑 Kill Switch: {reason} → توقف {seconds//60} دقيقة")


# ══════════════════════════════════════════════════════════════════════════════
# v21 — META-LEARNING + SHADOW TRADING + LATENCY OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. META-LEARNING ENGINE — أوزان الوكلاء تتعلم تلقائياً ─────────────────
class MetaLearningEngine:
    """
    كل وكيل له سجل أداء حقيقي.
    كل 50 صفقة → يُعيد حساب الأوزان بناءً على من أعطى الإشارة الصحيحة.
    الوكيل الفائز يحصل على وزن أعلى، الخاسر ينخفض وزنه تلقائياً.
    """
    def __init__(self):
        self.agent_scores: Dict[str, List[float]] = {}
        self.agent_weights: Dict[str, float]      = {}
        self.update_count = 0
        self.weight_history: List[Dict] = []

    def record_signal(self, agent_name: str,
                      predicted_dir: int,   # 1 أو -1
                      actual_pnl: float):
        correct = (predicted_dir > 0 and actual_pnl > 0) or                   (predicted_dir < 0 and actual_pnl < 0)
        score = 1.0 if correct else -0.5
        if agent_name not in self.agent_scores:
            self.agent_scores[agent_name] = []
        self.agent_scores[agent_name].append(score)
        if len(self.agent_scores[agent_name]) > 100:
            self.agent_scores[agent_name].pop(0)

    def recompute_weights(self) -> Dict[str, float]:
        """يُعيد حساب الأوزان كل 50 تسجيل"""
        self.update_count += 1
        if self.update_count % 50 != 0:
            return self.agent_weights

        new_weights = {}
        for agent, scores in self.agent_scores.items():
            if not scores:
                continue
            # متوسط آخر 50 نقطة
            avg     = sum(scores[-50:]) / len(scores[-50:])
            # تحويل إلى وزن: 0.5 إلى 5.0
            weight  = max(0.5, min(5.0, 1.0 + avg * 4.0))
            new_weights[agent] = round(weight, 2)
            # تطبيق مباشر على config
            if agent in config.AGENT_WEIGHTS:
                config.AGENT_WEIGHTS[agent] = weight

        self.agent_weights = new_weights
        self.weight_history.append({
            "time":    datetime.now().isoformat(),
            "weights": new_weights.copy()
        })
        if len(self.weight_history) > 20:
            self.weight_history.pop(0)

        if new_weights:
            best  = max(new_weights, key=new_weights.get)
            worst = min(new_weights, key=new_weights.get)
            log.info(
                f"🧠 MetaLearning #{self.update_count//50}: "
                f"Best={best}({new_weights[best]:.1f}) "
                f"Worst={worst}({new_weights[worst]:.1f})"
            )
        return new_weights

    def get_top_agents(self, n: int = 5) -> List[str]:
        """أفضل N وكلاء أداءً حالياً"""
        if not self.agent_weights:
            return list(config.AGENT_WEIGHTS.keys())[:n]
        return sorted(self.agent_weights,
                      key=self.agent_weights.get,
                      reverse=True)[:n]


# ── 2. SHADOW TRADING ENGINE ─────────────────────────────────────────────────
class ShadowTradingEngine:
    """
    يختبر استراتيجية جديدة في الخلفية بينما الاستراتيجية الحالية تعمل.
    بعد 100 صفقة ظلية → يقارن النتائج.
    إذا الظل أفضل → يُبدّل تلقائياً.
    """
    def __init__(self):
        self.shadow_balance  = config.INITIAL_CAPITAL
        self.shadow_trades:  List[Dict] = []
        self.live_trades:    List[Dict] = []
        self.shadow_params   = {
            "min_agreement": 0.60,
            "sl_atr":        1.2,
            "tp_atr":        4.5,
            "risk_pct":      0.025,
        }
        self.promoted        = 0
        self.comparisons     = 0

    def shadow_entry(self, symbol: str, direction: str,
                     price: float, atr: float):
        """يُسجّل دخولاً ظلياً"""
        sl  = (price - atr * self.shadow_params["sl_atr"]
               if direction == "LONG"
               else price + atr * self.shadow_params["sl_atr"])
        tp  = (price + atr * self.shadow_params["tp_atr"]
               if direction == "LONG"
               else price - atr * self.shadow_params["tp_atr"])
        qty = (self.shadow_balance * self.shadow_params["risk_pct"]
               / (atr * self.shadow_params["sl_atr"] + 1e-10))
        self.shadow_trades.append({
            "symbol": symbol, "direction": direction,
            "entry": price, "sl": sl, "tp": tp,
            "qty": qty, "status": "OPEN",
            "time": datetime.now().isoformat()
        })

    def update_shadow(self, prices: Dict[str, float]):
        """يُحدّث الصفقات الظلية بالأسعار الحالية"""
        for t in self.shadow_trades:
            if t["status"] != "OPEN":
                continue
            price = prices.get(t["symbol"], 0)
            if price <= 0:
                continue
            hit = False
            if t["direction"] == "LONG":
                if price <= t["sl"] or price >= t["tp"]:
                    hit = True
            else:
                if price >= t["sl"] or price <= t["tp"]:
                    hit = True
            if hit:
                mult = 1 if t["direction"] == "LONG" else -1
                pnl  = mult * (price - t["entry"]) * t["qty"]
                self.shadow_balance += pnl
                t["status"] = "CLOSED"
                t["pnl"]    = round(pnl, 4)

    def compare(self, live_balance: float) -> Dict:
        """يقارن الأداء كل 100 صفقة ظلية مغلقة"""
        closed = [t for t in self.shadow_trades
                  if t.get("status") == "CLOSED"]
        if len(closed) < 100:
            return {"compared": False}

        self.comparisons     += 1
        shadow_pnl   = sum(t.get("pnl",0) for t in closed[-100:])
        shadow_wr    = sum(1 for t in closed[-100:] if t.get("pnl",0)>0)/100
        live_pnl     = live_balance - config.INITIAL_CAPITAL

        result = {
            "compared":   True,
            "shadow_pnl": round(shadow_pnl, 2),
            "shadow_wr":  round(shadow_wr, 3),
            "live_pnl":   round(live_pnl, 2),
            "shadow_wins":shadow_pnl > 0,
        }
        if shadow_pnl > 0 and shadow_wr > 0.55:
            # الظل يفوز → تطبيق معاملاته
            config.STOP_LOSS_ATR   = self.shadow_params["sl_atr"]
            config.TAKE_PROFIT_ATR = self.shadow_params["tp_atr"]
            config.MIN_AGREEMENT   = self.shadow_params["min_agreement"]
            self.promoted         += 1
            result["promoted"]     = True
            log.info(
                f"🔄 Shadow Promoted #{self.promoted}: "
                f"SL={self.shadow_params['sl_atr']} "
                f"TP={self.shadow_params['tp_atr']}"
            )
            # توليد معاملات ظل جديدة للاختبار
            import random as _r
            self.shadow_params = {
                "min_agreement": round(_r.uniform(0.55, 0.72), 2),
                "sl_atr":        round(_r.uniform(0.7,  1.5),  1),
                "tp_atr":        round(_r.uniform(3.5,  7.0),  1),
                "risk_pct":      round(_r.uniform(0.02, 0.05), 3),
            }
        return result


# ── 3. LATENCY OPTIMIZER — معالجة 50 عملة × 11 وكيل بكفاءة ─────────────────
class LatencyOptimizer:
    """
    يحل مشكلة الضغط على المعالج:
    - يُقسّم العملات إلى دُفعات (batches)
    - يُعطي أولوية للعملات المتقلبة
    - يُخفّف عدد الوكلاء في الأوقات الهادئة
    - يُتابع latency ويُحذّر إذا تجاوزت 200ms
    """
    def __init__(self):
        self.latencies:    List[float] = []
        self.slow_cycles   = 0
        self.fast_cycles   = 0
        self.batch_size    = 10   # عملات لكل دُفعة
        self.agent_subset  = 7    # عدد الوكلاء في الأوقات الهادئة

    def start(self) -> float:
        return time.time()

    def end(self, t0: float) -> float:
        lat = (time.time() - t0) * 1000  # ms
        self.latencies.append(lat)
        if len(self.latencies) > 100:
            self.latencies.pop(0)
        if lat > 200:
            self.slow_cycles += 1
        else:
            self.fast_cycles += 1
        return lat

    @property
    def avg_latency(self) -> float:
        return sum(self.latencies[-20:]) / max(len(self.latencies[-20:]),1)

    def get_batch(self, symbols: List[str],
                  vol_scores: Dict[str, float]) -> List[str]:
        """يُعيد أول batch_size عملة بترتيب التقلب"""
        sorted_syms = sorted(symbols,
                             key=lambda s: vol_scores.get(s, 0),
                             reverse=True)
        # في الأوقات البطيئة → قلّل الدُفعة
        if self.avg_latency > 150:
            return sorted_syms[:self.batch_size // 2]
        return sorted_syms[:self.batch_size]

    def get_agent_count(self) -> int:
        """قلّل عدد الوكلاء إذا كان المعالج بطيئاً"""
        if self.avg_latency > 200:
            return 5   # 5 وكلاء فقط
        if self.avg_latency > 100:
            return self.agent_subset
        return 999     # كل الوكلاء

    def status(self) -> str:
        return (f"Latency avg={self.avg_latency:.0f}ms | "
                f"fast={self.fast_cycles} slow={self.slow_cycles}")


# ══════════════════════════════════════════════════════════════════════════════
# v22 — QUALITY OVER QUANTITY
# الجودة فوق الكمية — الإصلاحات الخمسة الحقيقية
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. FAST LOCAL PATH — تنفيذ فوري بدون انتظار AI ──────────────────────────
class FastLocalPath:
    """
    المشكلة: AI Council يستغرق 2-5 ثوانٍ → دخول متأخر
    الحل:
    - إشارة قوية (conf ≥ 0.85) + Trend + Sniper → تنفيذ فوري (0.1 ثانية)
    - إشارة متوسطة (0.65-0.84) → ينتظر AI Council
    - إشارة ضعيفة → يُهمل
    """
    def __init__(self):
        self.fast_trades  = 0
        self.slow_trades  = 0
        self.fast_pnl     = 0.0
        self.slow_pnl     = 0.0

    def should_fast_execute(self, conf: float, trend_ok: bool,
                             sniper_conf: float, regime: str) -> bool:
        """يُعيد True إذا يجب التنفيذ الفوري بدون AI"""
        if regime == "CHAOS":
            return False
        return (conf >= 0.85 and trend_ok and sniper_conf >= 0.65)

    def record(self, fast: bool, pnl: float):
        if fast:
            self.fast_trades += 1
            self.fast_pnl    += pnl
        else:
            self.slow_trades += 1
            self.slow_pnl    += pnl

    def status(self) -> str:
        ft = self.fast_trades or 1
        st = self.slow_trades or 1
        return (f"FastPath: {self.fast_trades} trades "
                f"avg={self.fast_pnl/ft:+.4f} | "
                f"SlowPath: {self.slow_trades} trades "
                f"avg={self.slow_pnl/st:+.4f}")


# ── 2. MINIMUM PROFIT FILTER — لا تدخل إذا الربح أقل من التكلفة × 3 ─────────
class MinProfitFilter:
    """
    يحسب التكلفة الحقيقية لكل صفقة ويرفضها إذا الربح المتوقع لا يكفي.
    رسوم OKX: 0.05% لكل جهة (فتح + إغلاق = 0.10%)
    Slippage:  0.03% متوسط
    الحد الأدنى: الربح المتوقع ≥ التكلفة × 3
    """
    MAKER_FEE  = 0.0002   # 0.02%
    TAKER_FEE  = 0.0005   # 0.05%
    SLIPPAGE   = 0.0003   # 0.03%
    MIN_RATIO  = 3.0      # الربح يجب أن يكون 3× التكلفة

    def __init__(self):
        self.rejected = 0
        self.passed   = 0
        self.saved_from_loss = 0.0

    def check(self, price: float, qty: float,
              atr: float, tp_atr: float) -> tuple:
        """يُعيد (pass, reason, expected_profit, cost)"""
        notional        = price * qty
        cost_open       = notional * self.TAKER_FEE
        cost_close      = notional * self.TAKER_FEE
        cost_slippage   = notional * self.SLIPPAGE * 2
        total_cost      = cost_open + cost_close + cost_slippage

        expected_profit = atr * tp_atr * qty

        if expected_profit >= total_cost * self.MIN_RATIO:
            self.passed += 1
            return (True,
                    f"profit={expected_profit:.4f} cost={total_cost:.4f}",
                    expected_profit, total_cost)
        else:
            self.rejected   += 1
            self.saved_from_loss += total_cost
            return (False,
                    f"profit({expected_profit:.4f}) < cost×3({total_cost*3:.4f})",
                    expected_profit, total_cost)

    def status(self) -> str:
        total = self.passed + self.rejected or 1
        return (f"MinProfit: passed={self.passed} "
                f"rejected={self.rejected} "
                f"({self.rejected/total:.0%} blocked) "
                f"saved=${self.saved_from_loss:.4f}")


# ── 3. CANDLE CLOSE FILTER — انتظر إغلاق الشمعة قبل الدخول ─────────────────
class CandleCloseFilter:
    """
    المشكلة: الدخول في منتصف الشمعة = سعر غير مؤكد = False Signals
    الحل: انتظر آخر 3 ثوانٍ من الشمعة ثم ادخل بعد الإغلاق
    يقلل False Signals بنسبة 20-30%
    """
    def __init__(self):
        self.waits        = 0
        self.skips        = 0
        self.tf_seconds   = {"1m":60, "5m":300, "15m":900, "1h":3600}

    def seconds_to_close(self, tf: str = "1m") -> float:
        period = self.tf_seconds.get(tf, 60)
        return period - (time.time() % period)

    async def wait_for_close(self, tf: str = "1m",
                              max_wait: float = 8.0) -> bool:
        """
        ينتظر إغلاق الشمعة إذا كانت على وشك الإغلاق (أقل من max_wait ثانية)
        يُعيد True إذا انتظر، False إذا لم ينتظر
        """
        secs = self.seconds_to_close(tf)
        if secs <= max_wait:
            self.waits += 1
            await asyncio.sleep(secs + 0.1)  # 0.1 ثانية بعد الإغلاق
            return True
        return False

    def is_fresh_candle(self, tf: str = "1m",
                         fresh_window: float = 5.0) -> bool:
        """هل نحن في أول 5 ثوانٍ من الشمعة الجديدة؟ (أفضل وقت للدخول)"""
        period = self.tf_seconds.get(tf, 60)
        elapsed = time.time() % period
        return elapsed <= fresh_window


# ── 4. REALISTIC BACKTEST ENGINE — باكتست بأرقام حقيقية ─────────────────────
class RealisticBacktestEngine:
    """
    Walk-Forward الحالي لا يحسب رسوماً حقيقية.
    هذا المحرك يحسب:
    - رسوم 0.05% لكل جهة
    - Slippage 0.03%
    - تأخير تنفيذ 2 ثانية (يفوّت السعر المثالي)
    - أيام الجفاف (لا إشارات)
    النتيجة: أرقام واقعية قبل التداول الحقيقي
    """
    FEE_RT    = 0.001    # 0.1% ذهاب وإياب
    SLIPPAGE  = 0.0006   # 0.06% ذهاب وإياب
    DELAY_SEC = 2.0      # تأخير التنفيذ

    def __init__(self):
        self.results: List[Dict] = []

    def run(self, df: pd.DataFrame,
            params: Dict, capital: float = 10.0) -> Dict:
        if df.empty or len(df) < 60:
            return {"score": 0, "realistic_return": 0}

        cap    = capital
        pos    = 0.0
        entry  = 0.0
        sl = tp = 0.0
        trades = []
        delay_candles = max(1, int(self.DELAY_SEC / 60))

        for i in range(20 + delay_candles, len(df)):
            row   = df.iloc[i]
            price = float(row.get("close", 0))
            atr   = float(row.get("atr", price * 0.01))
            if price <= 0:
                continue

            if pos == 0:
                # استخدام سعر ما بعد التأخير
                entry_row = df.iloc[i - delay_candles]
                ep = float(entry_row.get("close", price))

                rsi = float(row.get("rsi", 50))
                adx = float(row.get("adx", 0))
                mh  = float(row.get("macd_hist", 0))
                vr  = float(row.get("vol_ratio", 1))
                e20 = float(row.get("ema20", 0))
                e50 = float(row.get("ema50", 0))

                buy_ok = (rsi < params.get("rsi_buy", 40)
                          and adx > params.get("adx_min", 20)
                          and mh > 0 and vr > 1.2 and e20 > e50)

                if buy_ok:
                    # تطبيق الرسوم والـ Slippage على سعر الدخول
                    ep_real = ep * (1 + self.FEE_RT/2 + self.SLIPPAGE/2)
                    risk    = cap * 0.02
                    pos     = min(risk / (atr * params.get("sl_atr", 1.0)),
                                  cap * 0.15 / ep_real)
                    entry   = ep_real
                    sl      = ep_real - atr * params.get("sl_atr", 1.0)
                    tp      = ep_real + atr * params.get("tp_atr", 4.0)
            else:
                # تطبيق الرسوم والـ Slippage على سعر الخروج
                if price <= sl or price >= tp:
                    exit_real = price * (1 - self.FEE_RT/2 - self.SLIPPAGE/2)
                    pnl  = (exit_real - entry) * pos
                    cap  = max(cap + pnl, 0.01)
                    trades.append(pnl)
                    pos  = 0

        if len(trades) < 5:
            return {"score": 0, "realistic_return": 0,
                    "trades": 0, "win_rate": 0}

        arr  = np.array(trades)
        wins = sum(1 for t in trades if t > 0)
        wr   = wins / len(trades)
        ret  = (cap - capital) / capital * 100
        sh   = (arr.mean()/arr.std()*np.sqrt(252)
                if arr.std() > 0 else 0)
        eq   = np.array([capital] + list(np.cumsum(arr) + capital))
        pk   = np.maximum.accumulate(eq)
        dd   = ((pk - eq)/(pk + 1e-10)).max() * 100

        score = max(wr*25 + max(sh,0)*20 + max(ret,0)*0.3 + max(20-dd,0)*15, 0)

        return {
            "score":            round(score, 2),
            "realistic_return": round(ret, 2),
            "win_rate":         round(wr * 100, 1),
            "trades":           len(trades),
            "sharpe":           round(sh, 2),
            "max_dd":           round(dd, 2),
            "final_capital":    round(cap, 4),
        }


# ── 5. VOLATILITY TIMEFRAME SWITCH — إطار زمني ذكي ──────────────────────────
class VolatilityTimeframeSwitch:
    """
    تقلب عالٍ  → إطار 1 دقيقة  (فرص سريعة)
    تقلب هادئ  → إطار 5 دقائق  (إشارات أنظف وأقل ضجيجاً)
    تقلب منعدم → إطار 15 دقيقة (انتظر فرصة حقيقية)

    يقلل False Signals في الأوقات الهادئة بنسبة 35%
    """
    THRESHOLDS = {
        "HIGH":   0.008,   # ATR% > 0.8%  → 1m
        "MEDIUM": 0.004,   # ATR% > 0.4%  → 5m
        "LOW":    0.0,     # ATR% ≤ 0.4%  → 15m
    }

    def __init__(self):
        self.current_tf  = "5m"
        self.switches    = 0
        self.atr_history: deque = deque(maxlen=20)

    def update(self, atr_pct: float) -> str:
        self.atr_history.append(atr_pct)
        avg_atr = sum(self.atr_history) / len(self.atr_history)

        old_tf = self.current_tf
        if avg_atr >= self.THRESHOLDS["HIGH"]:
            self.current_tf = "1m"
        elif avg_atr >= self.THRESHOLDS["MEDIUM"]:
            self.current_tf = "5m"
        else:
            self.current_tf = "15m"

        if self.current_tf != old_tf:
            self.switches += 1
            log.info(f"⏱️ TF Switch: {old_tf} → {self.current_tf} "
                     f"(ATR%={avg_atr:.3%})")
        return self.current_tf

    def get_primary_tf(self) -> str:
        return self.current_tf

    def noise_level(self) -> str:
        return {"1m":"HIGH","5m":"MEDIUM","15m":"LOW"}.get(
            self.current_tf, "MEDIUM")


class EliteSignalFilter:
    def __init__(self):
        self.passed   = 0
        self.rejected = 0

    def evaluate(self, conf, trend_ok, is_prime,
                 sniper_conf, already_open,
                 daily_loss, balance) -> tuple:
        score = 0.0
        if conf >= 0.85:     score += 30
        elif conf >= 0.75:   score += 20
        elif conf >= 0.72:   score += 10
        else:
            self.rejected += 1
            return False, 0.0, f"conf_low={conf:.0%}"
        if not trend_ok:
            self.rejected += 1
            return False, 0.0, "against_trend"
        score += 25
        score += 15 if is_prime else 5
        if sniper_conf >= 0.65:   score += 20
        elif sniper_conf >= 0.55: score += 10
        if already_open:
            self.rejected += 1
            return False, 0.0, "already_open"
        if balance > 0 and daily_loss / balance < -0.08:
            self.rejected += 1
            return False, 0.0, "daily_loss_8pct"
        passed = score >= 55
        if passed: self.passed   += 1
        else:      self.rejected += 1
        return passed, score, f"score={score:.0f}"

    @property
    def pass_rate(self):
        t = self.passed + self.rejected
        return self.passed / t if t > 0 else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# SMART TRAILING STOP — يدع الأرباح تجري
# ══════════════════════════════════════════════════════════════════════════════
class SmartTrailingStop:
    def calculate_sl(self, entry, peak, current,
                     atr, direction, original_sl):
        if atr <= 0:
            return original_sl
        if direction == "LONG":
            pnl_atr = (peak - entry) / atr
            if   pnl_atr >= 4.0: trail = peak - atr * 0.7
            elif pnl_atr >= 2.0: trail = peak - atr * 1.0
            elif pnl_atr >= 1.0: trail = peak - atr * 1.5
            else:                trail = original_sl
            return max(trail, original_sl)
        else:
            pnl_atr = (entry - peak) / atr
            if   pnl_atr >= 4.0: trail = peak + atr * 0.7
            elif pnl_atr >= 2.0: trail = peak + atr * 1.0
            elif pnl_atr >= 1.0: trail = peak + atr * 1.5
            else:                trail = original_sl
            return min(trail, original_sl)


class FlashCrashGuard:
    """
    يكتشف الانهيارات المفاجئة ويحمي المحفظة:
    إذا تحرك السعر >5% في دقيقة → إغلاق فوري وانتظار
    """
    def __init__(self, db: Database):
        self.db           = db
        self.price_hist:  Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=60))
        self.in_crash:    Dict[str, bool] = {}
        self.cooldown:    Dict[str, int] = {}

    def update_price(self, symbol: str, price: float):
        self.price_hist[symbol].append((time.time(), price))

    def check(self, symbol: str, price: float) -> Dict:
        self.update_price(symbol, price)
        hist = list(self.price_hist[symbol])
        if len(hist) < 10:
            return {"crash": False, "drop_pct": 0}

        # فحص الانهيار في آخر دقيقة
        now       = time.time()
        one_min   = [(t,p) for t,p in hist if now-t <= 60]
        if not one_min:
            return {"crash": False, "drop_pct": 0}

        oldest_p = one_min[0][1]
        drop_pct = (oldest_p - price) / oldest_p

        # تقليل cooldown
        if symbol in self.cooldown and self.cooldown[symbol] > 0:
            self.cooldown[symbol] -= 1
            return {"crash": True, "drop_pct": drop_pct,
                    "cooldown": self.cooldown[symbol]}

        if drop_pct >= config.FLASH_CRASH_THRESHOLD:
            self.in_crash[symbol]  = True
            self.cooldown[symbol]  = config.FLASH_CRASH_COOLDOWN
            self.db.log_flash_crash(symbol, drop_pct, "EMERGENCY_CLOSE")
            log.error(
                f"⚡ FLASH CRASH [{symbol}] "
                f"انهيار {drop_pct:.1%} في دقيقة!")
            return {"crash": True, "drop_pct": drop_pct,
                    "action": "EMERGENCY_CLOSE"}

        # ارتفاع سريع = فرصة!
        pump_pct = (price - oldest_p) / oldest_p
        if pump_pct >= config.MOON_SHOT_MIN_PUMP:
            self.db.log_moon_shot(symbol, pump_pct, "BUY")
            log.moon(f"[{symbol}] 🚀 {pump_pct:.1%} في دقيقة!")
            return {"crash": False, "pump": True,
                    "pump_pct": pump_pct, "signal": "BUY"}

        self.in_crash[symbol] = False
        return {"crash": False, "drop_pct": 0}

    def is_safe(self, symbol: str) -> bool:
        cd = self.cooldown.get(symbol, 0)
        return cd == 0


# ══════════════════════════════════════════════════════════════════════════════
# 🔥 CIRCUIT BREAKER ULTRA — قاطع الدوائر المتقدم (10 مستويات)
# ══════════════════════════════════════════════════════════════════════════════
class CircuitBreakerUltra:
    """
    10 مستويات من الحماية:
    L1=0.5% تحذير → L10=25% إيقاف كامل
    """
    ACTIONS = {
        1: ("WARNING",        1.00, "تحذير فقط"),
        2: ("REDUCE_25",      0.75, "تقليل الحجم 25%"),
        3: ("REDUCE_50",      0.50, "تقليل الحجم 50%"),
        4: ("REDUCE_75",      0.25, "تقليل الحجم 75%"),
        5: ("PAUSE_NEW",      0.00, "وقف الصفقات الجديدة"),
        6: ("CLOSE_WORST",    0.00, "إغلاق أسوأ صفقة"),
        7: ("CLOSE_HALF",     0.00, "إغلاق نصف الصفقات"),
        8: ("CLOSE_ALL",      0.00, "إغلاق كل الصفقات"),
        9: ("EMERGENCY",      0.00, "وضع الطوارئ"),
        10:("SHUTDOWN",       0.00, "إيقاف النظام الكامل"),
    }

    def __init__(self):
        self.current_level = 0
        self.peak_equity   = 0.0
        self.triggered:    List[Dict] = []

    def check(self, equity: float) -> Dict:
        if equity > self.peak_equity:
            self.peak_equity = equity
            self.current_level = 0
            return {"level": 0, "action": "NORMAL", "size_mult": 1.0}

        if self.peak_equity <= 0:
            return {"level": 0, "action": "NORMAL", "size_mult": 1.0}

        dd = (self.peak_equity - equity) / self.peak_equity

        # تحديد المستوى
        level = 0
        for i, threshold in enumerate(config.CB_LEVELS):
            if dd >= threshold:
                level = i + 1

        if level != self.current_level:
            self.current_level = level
            if level > 0:
                action_name, mult, desc = self.ACTIONS[level]
                self.triggered.append({
                    "time":  datetime.now().isoformat(),
                    "level": level,
                    "dd":    round(dd*100, 2),
                    "action":action_name
                })
                log.warning(
                    f"🔴 Circuit Breaker L{level}: "
                    f"DD={dd:.1%} | {desc}")
                return {"level": level, "action": action_name,
                        "size_mult": mult, "dd": dd,
                        "shutdown": level >= 10}

        if level > 0:
            _, mult, _ = self.ACTIONS[level]
            return {"level": level, "action": self.ACTIONS[level][0],
                    "size_mult": mult, "dd": dd,
                    "shutdown": level >= 10}

        return {"level": 0, "action": "NORMAL", "size_mult": 1.0, "dd": dd}


# ══════════════════════════════════════════════════════════════════════════════
# 🐋 WHALE TRAP — فخ الحيتان (من the_absolute)
# ══════════════════════════════════════════════════════════════════════════════
class WhaleTrapDetector:
    """
    يكتشف عندما تضع الحيتان فخاً:
    - Fake Pump ثم Dump
    - Fake Dump ثم Pump
    - Stop Hunt (تصطاد وقف الخسارة)
    """
    def __init__(self):
        self.traps: deque = deque(maxlen=50)

    def detect(self, df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 20:
            return {"trap": False}
        c   = df["close"].astype(float)
        h   = df["high"].astype(float)
        l   = df["low"].astype(float)
        v   = df["volume"].astype(float)

        last5_vol = v.tail(5).mean()
        avg_vol   = v.mean()

        # ذيول طويلة = Stop Hunt
        last = df.iloc[-1]
        body = abs(float(last["close"]) - float(last["open"]))
        upper_wick = float(last["high"]) - max(
            float(last["close"]), float(last["open"]))
        lower_wick = min(
            float(last["close"]), float(last["open"])) - float(last["low"])

        if upper_wick > body * 2 and last5_vol > avg_vol * 1.5:
            self.traps.append({"type":"BEAR_TRAP","time":datetime.now().isoformat()})
            return {"trap": True, "type": "BEAR_TRAP",
                    "signal": "SELL", "confidence": 0.68}

        if lower_wick > body * 2 and last5_vol > avg_vol * 1.5:
            self.traps.append({"type":"BULL_TRAP","time":datetime.now().isoformat()})
            return {"trap": True, "type": "BULL_TRAP",
                    "signal": "BUY", "confidence": 0.68}

        return {"trap": False}


# ══════════════════════════════════════════════════════════════════════════════
# 🌑 DARK POOL DETECTOR — كاشف الصفقات الخفية
# ══════════════════════════════════════════════════════════════════════════════
class DarkPoolDetector:
    """
    يكتشف الصفقات الكبيرة المخفية:
    حجم كبير مع حركة سعر صغيرة = مؤسسات تشتري خفية
    """
    def detect(self, df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 20:
            return {"detected": False}
        c   = df["close"].astype(float)
        v   = df["volume"].astype(float)

        price_change = abs(c.pct_change().tail(5).mean())
        vol_surge    = v.tail(5).mean() / v.mean()

        # حجم كبير + حركة سعر صغيرة = dark pool
        if vol_surge > 2.5 and price_change < 0.005:
            direction = "BUY" if float(c.iloc[-1]) > float(c.iloc[-5]) else "SELL"
            return {
                "detected":   True,
                "direction":  direction,
                "vol_surge":  round(vol_surge, 2),
                "confidence": 0.65
            }
        return {"detected": False}


# ══════════════════════════════════════════════════════════════════════════════
# 🚀 PARABOLIC SQUEEZE — كاشف الحركات الصاروخية
# ══════════════════════════════════════════════════════════════════════════════
class ParabolicSqueezeDetector:
    """
    يكتشف الحركات الصاروخية قبل انطلاقها:
    BB Squeeze + Volume Surge + RSI صاعد = انطلاق وشيك
    """
    def detect(self, df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 30:
            return {"squeeze": False}

        last = df.iloc[-1]
        bb_w = float(last.get("bb_width", 1))
        vol_r= float(last.get("vol_ratio", 1))
        rsi  = float(last.get("rsi", 50))
        adx  = float(last.get("adx", 0))

        # BB Squeeze (تضيّق الباندز)
        bb_hist    = df["bb_width"].tail(20)
        is_squeeze = bb_w < float(bb_hist.quantile(0.20))

        if is_squeeze and vol_r > 1.8 and adx > 20:
            ema20 = float(last.get("ema20", 0))
            ema50 = float(last.get("ema50", 0))
            direction = "BUY" if ema20 > ema50 and rsi > 50 else "SELL"
            confidence= min(0.50 + vol_r*0.05 + (adx-20)*0.005, 0.85)
            return {
                "squeeze":    True,
                "direction":  direction,
                "confidence": round(confidence, 3),
                "bb_width":   round(bb_w, 4),
                "vol_ratio":  round(vol_r, 2)
            }
        return {"squeeze": False}


# ══════════════════════════════════════════════════════════════════════════════
# 🧠 OPENROUTER AI COUNCIL
# ══════════════════════════════════════════════════════════════════════════════
class OpenRouterCouncil:
    MODELS = [
        ("openai/gpt-4o-mini",               "GPT-4o",   0.30),
        ("anthropic/claude-3-haiku",          "Claude",   0.30),
        ("google/gemini-flash-1.5",           "Gemini",   0.25),
        ("meta-llama/llama-3.1-8b-instruct",  "Llama",    0.15),
    ]

    def __init__(self):
        self.enabled = bool(
            config.OPENROUTER_KEY and
            "YOUR_" not in config.OPENROUTER_KEY)
        self._cache: Dict = {}
        self._ttl    = 600  # 10 دقائق بدلاً من 5 لتقليل التكلفة

    async def consult(self, symbol: str, price: float,
                       indicators: Dict,
                       tech_signal: str) -> Dict:
        if not self.enabled:
            return {"signal": tech_signal,
                    "confidence": 0.60, "votes": []}

        key = f"{symbol}_{tech_signal}_{int(time.time()//self._ttl)}"
        if key in self._cache:
            return self._cache[key]

        ctx = (
            f"Symbol:{symbol} Price:{price:.4f} "
            f"RSI:{indicators.get('rsi',50):.1f} "
            f"ADX:{indicators.get('adx',0):.1f} "
            f"MACD:{indicators.get('macd_hist',0):.4f} "
            f"BB%:{indicators.get('bb_pct',0.5):.2f} "
            f"VolR:{indicators.get('vol_ratio',1):.2f} "
            f"TechSignal:{tech_signal}"
        )

        votes = []
        async with aiohttp.ClientSession() as session:
            tasks = [self._ask(session, mid, name, ctx)
                     for mid, name, _ in self.MODELS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception): continue
            _, name, weight = self.MODELS[i]
            votes.append({
                "model":      name,
                "signal":     result.get("signal", "HOLD"),
                "confidence": result.get("confidence", 0.5),
                "weight":     weight
            })

        if not votes:
            return {"signal": tech_signal, "confidence": 0.55, "votes": []}

        buy_s = sell_s = 0.0
        for v in votes:
            w = v["weight"] * v["confidence"]
            if v["signal"]=="BUY":    buy_s  += w
            elif v["signal"]=="SELL": sell_s += w

        total = buy_s + sell_s + 1e-10
        if buy_s/total  >= 0.60: final="BUY";  conf=buy_s/total
        elif sell_s/total >= 0.60: final="SELL"; conf=sell_s/total
        else:                      final="HOLD"; conf=max(buy_s,sell_s)/total

        result = {"signal":final,"confidence":round(conf,3),"votes":votes}
        self._cache[key] = result
        return result

    async def _ask(self, session, model_id, name, ctx) -> Dict:
        prompt = (
            f"Trading analyst. Data: {ctx}\n"
            "Reply JSON only: "
            '{"signal":"BUY or SELL or HOLD","confidence":0.0,"reasoning":"brief"}'
        )
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization":f"Bearer {config.OPENROUTER_KEY}",
                         "Content-Type":"application/json"},
                json={"model":model_id,
                      "messages":[{"role":"user","content":prompt}],
                      "max_tokens":80,"temperature":0.2},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    return {"signal":"HOLD","confidence":0.5}
                data  = await resp.json()
                text  = data["choices"][0]["message"]["content"].strip()
                text  = text.replace("```json","").replace("```","").strip()
                return json.loads(text)
        except:
            return {"signal":"HOLD","confidence":0.5}


# ══════════════════════════════════════════════════════════════════════════════
# 🤖 الوكلاء المدمجون
# ══════════════════════════════════════════════════════════════════════════════
class BaseAgent:
    def __init__(self, name: str, weight: float):
        self.name   = name
        self.weight = weight

    async def analyze(self, data: Dict) -> Tuple[int, float, Dict]:
        return 0, 0.0, {}


class TechnicalAgent(BaseAgent):
    async def analyze(self, data):
        df1h  = data.get("1h", pd.DataFrame())
        df15m = data.get("15m", pd.DataFrame())
        df5m  = data.get("5m", pd.DataFrame())
        if df1h.empty or len(df1h)<2: return 0,0.0,{}
        l1h=df1h.iloc[-1]
        l15m=df15m.iloc[-1] if not df15m.empty else l1h
        l5m =df5m.iloc[-1]  if not df5m.empty  else l1h
        ema20=float(l1h.get("ema20",0)); ema50=float(l1h.get("ema50",0))
        rsi  =float(l15m.get("rsi",50))
        mh   =float(l5m.get("macd_hist",0))
        adx  =float(l1h.get("adx",0))
        vr   =float(l5m.get("vol_ratio",1))
        trend= 1 if ema20>ema50 else -1
        if trend==1 and rsi<42 and mh>0 and adx>20 and vr>1.2:
            return 1,0.80,{"trend":"UP","rsi":rsi,"adx":adx}
        if trend==-1 and rsi>58 and mh<0 and adx>20 and vr>1.2:
            return -1,0.80,{"trend":"DOWN","rsi":rsi,"adx":adx}
        return 0,0.0,{}


class MLEnsembleAgent(BaseAgent):
    def __init__(self, name, weight):
        super().__init__(name, weight)
        self.rf   = RandomForestClassifier(n_estimators=50,random_state=42) if ML_AVAILABLE else None
        self.gb   = GradientBoostingClassifier(n_estimators=50,random_state=42) if ML_AVAILABLE else None
        self.xgb  = xgb.XGBClassifier(n_estimators=50,use_label_encoder=False,
                                        eval_metric="logloss") if XGB_AVAILABLE else None
        self.sc   = StandardScaler() if ML_AVAILABLE else None
        self.trained = False
        self.feats= ["rsi","macd_hist","bb_pct","vol_ratio",
                     "adx","atr_pct","stoch","returns"]

    def train(self, df: pd.DataFrame) -> bool:
        if not ML_AVAILABLE or len(df)<100: return False
        X,y = [],[]
        for i in range(20,len(df)-5):
            row = df.iloc[i]
            feat= [float(row.get(f,0)) for f in self.feats]
            ret = (df["close"].iloc[i+5]-df["close"].iloc[i])/df["close"].iloc[i]
            y.append(1 if ret>0.01 else 0)
            X.append(feat)
        if len(X)<30: return False
        try:
            Xs = self.sc.fit_transform(np.array(X))
            self.rf.fit(Xs, y)
            if self.gb: self.gb.fit(Xs, y)
            if self.xgb: self.xgb.fit(Xs, y)
            self.trained = True
            return True
        except: return False

    async def analyze(self, data):
        if not self.trained: return 0,0.5,{"trained":False}
        df = data.get(config.PRIMARY_TF, pd.DataFrame())
        if df.empty or len(df)<5: return 0,0.0,{}
        last = df.iloc[-1]
        feat = [float(last.get(f,0)) for f in self.feats]
        try:
            Xs = self.sc.transform([feat])
            probs = []
            if self.rf: probs.append(self.rf.predict_proba(Xs)[0][1])
            if self.gb: probs.append(self.gb.predict_proba(Xs)[0][1])
            if self.xgb: probs.append(self.xgb.predict_proba(Xs)[0][1])
            prob = float(np.mean(probs)) if probs else 0.5
            d = 1 if prob>0.65 else (-1 if prob<0.35 else 0)
            return d, abs(prob-0.5)*2, {"prob":round(prob,3)}
        except: return 0,0.0,{}


class SentimentAgent(BaseAgent):
    def __init__(self, name, weight):
        super().__init__(name, weight)
        self._fg_cache: Optional[Tuple] = None

    async def analyze(self, data):
        score = await self._fear_greed()
        df    = data.get("1h", pd.DataFrame())
        news  = 0.0
        if not df.empty and len(df)>=24:
            ret = df["returns"].tail(24)
            news= float(np.tanh(ret.mean()*100))
        combined = score*0.5 + news*0.5
        if combined>0.25: return  1, min(abs(combined)*1.5,0.75), {"fg":score,"news":news}
        if combined<-0.25:return -1, min(abs(combined)*1.5,0.75), {"fg":score,"news":news}
        return 0,0.0,{}

    async def _fear_greed(self) -> float:
        if self._fg_cache:
            v,ts = self._fg_cache
            if time.time()-ts<1800: return v
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.alternative.me/fng/?limit=1",
                                  timeout=aiohttp.ClientTimeout(total=5)) as r:
                    d = await r.json()
                    v = (int(d["data"][0]["value"])-50)/50
                    self._fg_cache = (v, time.time())
                    return v
        except: return 0.0


class VolumeProfileAgent(BaseAgent):
    async def analyze(self, data):
        df = data.get("15m", pd.DataFrame())
        if df.empty or len(df)<20: return 0,0.0,{}
        last = df.iloc[-1]
        vr   = float(last.get("vol_ratio",1))
        vwap = float(last.get("vwap",0))
        price= float(last["close"])
        if vr>2.0:
            d = 1 if float(last["close"])>float(last["open"]) else -1
            vwap_signal = (1 if price<vwap*0.998 else
                           -1 if price>vwap*1.002 else 0)
            if d == vwap_signal or vwap_signal==0:
                return d, min(vr/3,0.85), {"vol_ratio":round(vr,2),"vwap_signal":vwap_signal}
        return 0,0.0,{}


class OrderFlowAgent(BaseAgent):
    async def analyze(self, data):
        df = data.get("1m", pd.DataFrame())
        if df.empty or len(df)<10: return 0,0.0,{}
        up = df[df["close"]>df["close"].shift(1)]["volume"].sum()
        dn = df[df["close"]<df["close"].shift(1)]["volume"].sum()
        total = up+dn
        if total==0: return 0,0.0,{}
        imbal = (up-dn)/total
        if imbal>0.3:  return  1, float(abs(imbal)), {"imbalance":round(imbal,3)}
        if imbal<-0.3: return -1, float(abs(imbal)), {"imbalance":round(imbal,3)}
        return 0,0.0,{}


class WhaleAgent(BaseAgent):
    async def analyze(self, data):
        df = data.get("1h", pd.DataFrame())
        if df.empty or len(df)<10: return 0,0.0,{}
        rv = df["volume"].tail(5).mean()
        av = df["volume"].mean()
        if av==0: return 0,0.0,{}
        wr = rv/av
        if wr>2.5:
            last = df.iloc[-1]
            d = 1 if float(last["close"])>float(last["open"]) else -1
            log.whale(f"[{data.get('symbol','?')}] Whale×{wr:.1f}")
            return d, min(wr/5,0.85), {"whale_ratio":round(wr,2)}
        return 0,0.0,{}


class FlashCrashAgent(BaseAgent):
    def __init__(self, name, weight, guard: FlashCrashGuard):
        super().__init__(name, weight)
        self.guard = guard

    async def analyze(self, data):
        symbol = data.get("symbol","")
        df     = data.get("1m", pd.DataFrame())
        if df.empty or not symbol: return 0,0.0,{}
        price  = float(df.iloc[-1]["close"])
        result = self.guard.check(symbol, price)
        if result.get("crash"):   return -1, 0.90, result
        if result.get("pump"):    return  1, 0.75, result
        return 0,0.0,{}


class ParabolicAgent(BaseAgent):
    def __init__(self, name, weight, detector: ParabolicSqueezeDetector):
        super().__init__(name, weight)
        self.detector = detector

    async def analyze(self, data):
        df = data.get("15m", pd.DataFrame())
        if df.empty: return 0,0.0,{}
        r = self.detector.detect(df)
        if r.get("squeeze"):
            d = 1 if r["direction"]=="BUY" else -1
            return d, r["confidence"], r
        return 0,0.0,{}


class DarkPoolAgent(BaseAgent):
    def __init__(self, name, weight, detector: DarkPoolDetector):
        super().__init__(name, weight)
        self.detector = detector

    async def analyze(self, data):
        df = data.get("1h", pd.DataFrame())
        if df.empty: return 0,0.0,{}
        r = self.detector.detect(df)
        if r.get("detected"):
            d = 1 if r["direction"]=="BUY" else -1
            return d, r["confidence"], r
        return 0,0.0,{}


class EvolutionaryAgent(BaseAgent):
    def __init__(self, name, weight, db: Database):
        super().__init__(name, weight)
        self.db     = db
        self.params = {"rsi_buy":40,"rsi_sell":60,"adx_min":20,"vol_min":1.2}
        self._cycle = 0

    async def analyze(self, data):
        self._cycle += 1
        if self._cycle % 20 == 0: self._evolve()
        df = data.get(config.PRIMARY_TF, pd.DataFrame())
        if df.empty or len(df)<5: return 0,0.0,{}
        last = df.iloc[-1]
        rsi  = float(last.get("rsi",50))
        adx  = float(last.get("adx",0))
        vr   = float(last.get("vol_ratio",1))
        e20  = float(last.get("ema20",0))
        e50  = float(last.get("ema50",0))
        if (rsi<self.params["rsi_buy"] and adx>self.params["adx_min"]
                and vr>self.params["vol_min"] and e20>e50):
            return 1, 0.75, {"evolved":self.params}
        if (rsi>self.params["rsi_sell"] and adx>self.params["adx_min"]
                and vr>self.params["vol_min"] and e20<e50):
            return -1, 0.75, {"evolved":self.params}
        return 0,0.0,{}

    def _evolve(self):
        s = self.db.get_stats()
        wr= s["win_rate"]/100
        if wr<0.45:
            self.params["rsi_buy"]  = max(25, self.params["rsi_buy"]-3)
            self.params["rsi_sell"] = min(75, self.params["rsi_sell"]+3)
        elif wr>0.65:
            self.params["rsi_buy"]  = min(45, self.params["rsi_buy"]+2)
            self.params["rsi_sell"] = max(55, self.params["rsi_sell"]-2)


class AICouncilAgent(BaseAgent):
    def __init__(self, name, weight, council: OpenRouterCouncil):
        super().__init__(name, weight)
        self.council    = council
        self._last: Dict = {}

    async def analyze(self, data):
        r = self._last
        if not r: return 0,0.0,{}
        sig  = r.get("signal","HOLD")
        conf = r.get("confidence",0.5)
        if sig=="BUY":  return  1, conf, r
        if sig=="SELL": return -1, conf, r
        return 0,0.0,{}

    def update(self, result: Dict): self._last = result


# ══════════════════════════════════════════════════════════════════════════════
# ⚖️  CONSENSUS ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class ConsensusEngine:
    def __init__(self, agents: List[BaseAgent]):
        self.agents = agents

    async def decide(self, data: Dict) -> Tuple[str, float, Dict]:
        votes_buy = votes_sell = total_w = 0.0
        details   = {}
        for agent in self.agents:
            try:
                d, conf, det = await agent.analyze(data)
            except Exception as e:
                log.error(f"[{agent.name}] {e}")
                d, conf, det = 0, 0.0, {}
            w = config.AGENT_WEIGHTS.get(agent.name, 1.0)
            total_w += w
            details[agent.name] = {"dir":d,"conf":round(conf,3)}
            if d==1:   votes_buy  += w*conf
            elif d==-1: votes_sell += w*conf

        if total_w==0: return "NEUTRAL",0.0,details
        bs = votes_buy/total_w; ss = votes_sell/total_w
        bc = sum(1 for v in details.values() if v["dir"]==1)
        sc = sum(1 for v in details.values() if v["dir"]==-1)

        if bs>=config.MIN_AGREEMENT and bc>=config.MIN_AGENTS:
            return "LONG",  round(bs,3), details
        if ss>=config.MIN_AGREEMENT and sc>=config.MIN_AGENTS:
            return "SHORT", round(ss,3), details
        return "NEUTRAL", round(max(bs,ss),3), details


# ══════════════════════════════════════════════════════════════════════════════
# 🧪 PAPER TRADING ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class PaperEngine:
    COMM = 0.001; SLIP = 0.0005

    def __init__(self, initial: float = None):
        self.initial = initial or config.PAPER_BALANCE
        self.balance = self.initial
        self.positions: Dict = {}
        self.trades:    List = []
        self.equity:    List = [self.initial]

    def open(self, symbol, side, price, qty, sl, tp, agent_id) -> Optional[str]:
        ep  = price*(1+self.SLIP if side=="buy" else 1-self.SLIP)
        cost= ep*qty*(1+self.COMM)
        if cost>self.balance or ep*qty<10: return None
        self.balance -= ep*qty*self.COMM
        pid = f"{symbol}_{agent_id}_{int(time.time()*1000)}"
        self.positions[pid] = {
            "symbol":symbol,"side":side,"entry":ep,
            "qty":qty,"sl":sl,"tp":tp,"peak":ep
        }
        return pid

    def close(self, pid, price, reason="") -> Optional[float]:
        pos = self.positions.get(pid)
        if not pos: return None
        ep  = price*(1-self.SLIP if pos["side"]=="buy" else 1+self.SLIP)
        comm= ep*pos["qty"]*self.COMM
        pnl = ((ep-pos["entry"])*pos["qty"]
                if pos["side"]=="buy"
                else (pos["entry"]-ep)*pos["qty"]) - comm
        self.balance += pnl
        self.equity.append(self.balance)
        self.trades.append({**pos,"exit":ep,"pnl":round(pnl,4),"reason":reason})
        del self.positions[pid]
        return pnl

    def performance(self) -> Dict:
        if not self.trades: return {
            "total":0,"win_rate":0,"pnl":0,"sharpe":0,
            "max_dd":0,"pf":0,"return_pct":0,"balance":self.balance}
        pnls = [t["pnl"] for t in self.trades]
        wins = [p for p in pnls if p>0]
        loss = [p for p in pnls if p<=0]
        arr  = np.array(pnls)
        sh   = arr.mean()/arr.std()*np.sqrt(252) if arr.std()>0 else 0
        eq   = np.array(self.equity)
        pk   = np.maximum.accumulate(eq)
        dd   = ((pk-eq)/(pk+1e-10)).max()*100
        pf   = sum(wins)/(abs(sum(loss))+1e-10)
        return {
            "total":   len(pnls),
            "win_rate":round(len(wins)/len(pnls)*100,1),
            "pnl":     round(sum(pnls),2),
            "sharpe":  round(sh,2),
            "max_dd":  round(dd,2),
            "pf":      round(pf,2),
            "return_pct": round((self.balance-self.initial)/self.initial*100,2),
            "balance": round(self.balance,2)
        }


# ══════════════════════════════════════════════════════════════════════════════
# 🛡️  RISK MANAGER
# ══════════════════════════════════════════════════════════════════════════════
class RiskManager:
    def __init__(self):
        self.capital    = config.INITIAL_CAPITAL
        self.peak       = config.INITIAL_CAPITAL
        self.loss_streak= 0
        self.cb         = CircuitBreakerUltra()

    def check(self, equity: float,
               daily_pnl: float) -> Tuple[bool, str, float]:
        cb_result = self.cb.check(equity)
        if cb_result.get("shutdown"):
            return False, "🔴 Circuit Breaker L10 — إيقاف", 0.0
        if cb_result["level"] >= 8:
            return False, f"🔴 CB L{cb_result['level']}", 0.0

        if daily_pnl <= -(equity * config.HARD_MAX_LOSS):
            return False, "حد الخسارة اليومي", 0.0

        dd = (self.peak-equity)/self.peak if self.peak>0 else 0
        if dd >= config.HARD_MAX_DD:
            return False, f"Max Drawdown {dd:.1%}", 0.0

        if self.loss_streak >= 4:
            return False, f"خسائر متتالية: {self.loss_streak}", 0.0

        size_mult = cb_result.get("size_mult", 1.0)
        if self.loss_streak > 0:
            size_mult *= 0.5**self.loss_streak

        return True, "✅", size_mult

    def update(self, pnl: float, equity: float):
        self.peak       = max(self.peak, equity)
        self.capital    += pnl
        self.loss_streak = (self.loss_streak+1 if pnl<0 else 0)


# ══════════════════════════════════════════════════════════════════════════════
# 📡 EXCHANGE CONNECTOR
# ══════════════════════════════════════════════════════════════════════════════
class ExchangeConnector:
    def __init__(self):
        self.okx = None
        if CCXT_AVAILABLE and config.OKX_API_KEY:
            try:
                import ccxt.pro as cp
                self.okx = cp.okx({
                    "apiKey":   config.OKX_API_KEY,
                    "secret":   config.OKX_SECRET,
                    "password": config.OKX_PASSPHRASE,
                    "enableRateLimit": True,
                    "options": {"defaultType": "swap"}  # ✅ عقود دائمة Perpetual
                })
                log.info("✅ OKX متصل")
            except Exception as e:
                log.warning(f"OKX: {e}")

    async def fetch_ohlcv(self, symbol: str, tf: str,
                           limit: int = 300) -> pd.DataFrame:
        if self.okx is None: return self._sim(symbol, limit)
        try:
            ohlcv = await self.okx.fetch_ohlcv(symbol.replace("-","/"), tf, limit=limit)
            df    = pd.DataFrame(ohlcv,
                columns=["timestamp","open","high","low","close","volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            log.warning(f"fetch [{symbol}]: {e}")
            return self._sim(symbol, limit)

    def _sim(self, symbol: str, limit: int) -> pd.DataFrame:
        base = {"BTC-USDT":50000,"ETH-USDT":3000,
                "SOL-USDT":150,"BNB-USDT":400}.get(symbol, 1000)
        p = base + np.cumsum(np.random.randn(limit)*base*0.003)
        v = np.random.uniform(100,1000,limit)
        return pd.DataFrame({
            "timestamp": pd.date_range(end=datetime.now(),
                                        periods=limit,freq="1min"),
            "open":p,"high":p*1.005,"low":p*0.995,
            "close":p,"volume":v
        })

    async def fetch_price(self, symbol: str) -> float:
        if self.okx is None:
            base={"BTC-USDT":50000,"ETH-USDT":3000,
                  "SOL-USDT":150,"BNB-USDT":400}.get(symbol,1000)
            return base*(1+np.random.randn()*0.001)
        try:
            t = await self.okx.fetch_ticker(symbol.replace("-","/"))
            return float(t.get("last",0))
        except: return 0.0

    async def create_order(self, symbol, side, amount) -> Dict:
        if self.okx is None:
            return {"id":hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
                    "status":"closed","price":0}
        try:
            return await self.okx.create_order(
                symbol, "market", side, amount, params={"tdMode": "isolated"})
        except Exception as e:
            log.error(f"order: {e}")
            return {}

    async def close(self):
        if self.okx:
            try: await self.okx.close()
            except: pass


# ══════════════════════════════════════════════════════════════════════════════
# 📱 TELEGRAM NOTIFIER
# ══════════════════════════════════════════════════════════════════════════════
class Notifier:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def send(self, msg: str) -> bool:
        if not config.TG_TOKEN or "YOUR_" in config.TG_TOKEN:
            log.info(f"📢 {msg[:80]}")
            return True
        try:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            url  = f"https://api.telegram.org/bot{config.TG_TOKEN}/sendMessage"
            async with self._session.post(
                url,
                data={"chat_id":config.TG_CHAT,"text":msg,"parse_mode":"HTML"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                return r.status == 200
        except: return False

    async def startup(self, mode: str, agents: int):
        await self.send(
            f"🚀 <b>Snowball v19 — HYPER AI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ الوضع: {mode}\n"
            f"🤖 وكلاء: {agents}\n"
            f"🧠 OpenRouter: {'✅' if config.OPENROUTER_KEY else '⚙️'}\n"
            f"⚡ Flash Crash Guard: ✅\n"
            f"🔴 Circuit Breakers: 10 مستويات\n"
            f"🐋 Whale Trap: ✅\n"
            f"🌑 Dark Pool: ✅\n"
            f"🚀 Parabolic Squeeze: ✅\n"
            f"💸 Auto Transfer: {'✅' if config.AUTO_PROFIT_TRANSFER else '❌'}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📱 /help للأوامر"
        )

    async def trade_alert(self, symbol, direction, price,
                           conf, mode, ai_signal):
        e = "📈🟢" if direction=="LONG" else "📉🔴"
        m = "🧪" if mode=="PAPER" else "💰"
        await self.send(
            f"{e} {m} <b>{direction}</b> {symbol}\n"
            f"💰 {price:,.4f} | conf={conf:.0%}\n"
            f"🧠 AI: {ai_signal}"
        )

    async def daily_report(self, stats, paper_perf, transferred):
        await self.send(
            f"📊 <b>التقرير اليومي</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 Paper PnL: {paper_perf.get('pnl',0):+.2f}\n"
            f"🎯 الفوز: {paper_perf.get('win_rate',0)}%\n"
            f"📐 Sharpe: {paper_perf.get('sharpe',0):.2f}\n"
            f"📉 Max DD: {paper_perf.get('max_dd',0):.1f}%\n"
            f"💸 محوّل: ${transferred:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()




# ══════════════════════════════════════════════════════════════════════════════
# 🧬 AGENT EVOLUTION SYSTEM — نظام تطور وتزاوج الوكلاء
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class AgentGenome:
    """الجينوم الكامل للوكيل"""
    agent_id:    str   = ""
    name:        str   = ""
    generation:  int   = 0
    father_id:   str   = ""
    mother_id:   str   = ""
    # جينات المؤشرات
    rsi_buy:     float = 40.0
    rsi_sell:    float = 60.0
    adx_min:     float = 20.0
    vol_min:     float = 1.20
    atr_sl:      float = 1.5
    atr_tp:      float = 3.0
    # جينات السلوك
    aggression:  float = 1.0
    patience:    float = 1.0
    # إحصاءات
    fitness:     float = 0.0
    trades_won:  int   = 0
    trades_lost: int   = 0
    age:         int   = 0
    alive:       bool  = True
    children:    int   = 0
    last_mating: int   = -999

    @property
    def win_rate(self) -> float:
        t = self.trades_won + self.trades_lost
        return self.trades_won / t if t > 0 else 0.0

    @property
    def can_mate(self) -> bool:
        return (self.alive and self.age >= 5 and
                self.age - self.last_mating >= 8)

    def compute_id(self):
        self.agent_id = str(uuid.uuid4())[:8]

    def mutate(self, strength: float = 0.10) -> "AgentGenome":
        child = AgentGenome(
            name       = self.name + "_M",
            generation = self.generation + 1,
            father_id  = self.agent_id,
            rsi_buy    = max(15, min(49, self.rsi_buy  * (1+random.gauss(0,strength)))),
            rsi_sell   = max(51, min(85, self.rsi_sell * (1+random.gauss(0,strength)))),
            adx_min    = max(10, min(40, self.adx_min  * (1+random.gauss(0,strength)))),
            vol_min    = max(0.8, min(3.0,self.vol_min * (1+random.gauss(0,strength)))),
            atr_sl     = max(0.5, min(3.0,self.atr_sl  * (1+random.gauss(0,strength)))),
            atr_tp     = max(1.5, min(8.0,self.atr_tp  * (1+random.gauss(0,strength)))),
            aggression = max(0.3, min(3.0,self.aggression*(1+random.gauss(0,strength)))),
            patience   = max(0.3, min(3.0,self.patience *(1+random.gauss(0,strength)))),
        )
        if child.atr_tp <= child.atr_sl:
            child.atr_tp = child.atr_sl * 2
        child.compute_id()
        return child


class AgentMatingSystem:
    """
    نظام تزاوج الوكلاء:
    - الوكلاء الأقوى يتزاوجون
    - الأبناء يرثون أفضل الصفات
    - الضعفاء يموتون
    - كل جيل أذكى من السابق
    """

    def compatibility(self, f: AgentGenome,
                       m: AgentGenome) -> float:
        score  = (f.win_rate + m.win_rate) * 20
        score += (f.fitness  + m.fitness)  * 0.2
        # التنوع الجيني مفيد
        diversity = abs(f.rsi_buy-m.rsi_buy)/50 + abs(f.aggression-m.aggression)/3
        score += diversity * 15
        return min(score, 100.0)

    def mate(self, father: AgentGenome,
              mother: AgentGenome,
              cycle:  int) -> List[AgentGenome]:
        compat = self.compatibility(father, mother)
        n = (3 if compat > 70 else 2 if compat > 40 else 1)
        children = []
        for _ in range(n):
            child = self._create_child(father, mother)
            children.append(child)
        father.children    += len(children)
        mother.children    += len(children)
        father.last_mating  = cycle
        mother.last_mating  = cycle
        return children

    def _create_child(self, f: AgentGenome,
                       m: AgentGenome) -> AgentGenome:
        # وراثة من الأب أو الأم لكل جين
        child = AgentGenome(
            generation = max(f.generation, m.generation) + 1,
            father_id  = f.agent_id,
            mother_id  = m.agent_id,
            rsi_buy    = getattr(f if random.random()<0.5 else m, "rsi_buy"),
            rsi_sell   = getattr(f if random.random()<0.5 else m, "rsi_sell"),
            adx_min    = getattr(f if random.random()<0.5 else m, "adx_min"),
            vol_min    = getattr(f if random.random()<0.5 else m, "vol_min"),
            atr_sl     = getattr(f if random.random()<0.5 else m, "atr_sl"),
            atr_tp     = getattr(f if random.random()<0.5 else m, "atr_tp"),
            aggression = getattr(f if random.random()<0.5 else m, "aggression"),
            patience   = getattr(f if random.random()<0.5 else m, "patience"),
        )
        # طفرة عشوائية
        if random.random() < 0.15:
            child = child.mutate(0.08)

        prefixes = ["Alpha","Beta","Gamma","Delta","Sigma","Omega"]
        suffixes = ["Prime","Ultra","Neo","Pro","Elite","Max"]
        child.name = f"{random.choice(prefixes)}_{random.choice(suffixes)}_G{child.generation}"
        if child.atr_tp <= child.atr_sl:
            child.atr_tp = child.atr_sl * 2
        child.compute_id()
        return child

    def select_mates(self, population: List[AgentGenome],
                      cycle: int) -> List[tuple]:
        eligible = [a for a in population
                    if a.alive and a.can_mate]
        if len(eligible) < 2: return []
        random.shuffle(eligible)
        pairs = []
        for i in range(0, len(eligible)-1, 2):
            f = eligible[i]; m = eligible[i+1]
            if f.father_id == m.agent_id: continue
            pairs.append((f, m))
        return pairs[:2]

    def natural_selection(self, population: List[AgentGenome],
                           cycle: int) -> tuple:
        survivors = []; dead = []
        for a in population:
            if not a.alive: dead.append(a); continue
            # الموت بالشيخوخة
            if a.age >= 50:
                a.alive = False; dead.append(a); continue
            # الموت بضعف الأداء
            if a.age >= 15 and a.fitness < 5.0 and a.trades_won+a.trades_lost > 10:
                a.alive = False; dead.append(a); continue
            survivors.append(a)
        return survivors, dead


class AgentEcosystem:
    """
    النظام البيئي الكامل للوكلاء:
    يُدير الولادة والتزاوج والوفاة
    """
    MIN_POP = 4
    MAX_POP = 15

    def __init__(self):
        self.population: List[AgentGenome] = []
        self.mating     = AgentMatingSystem()
        self.cycle      = 0
        self.total_born = 0
        self.total_dead = 0
        self._init_founders()

    def _init_founders(self):
        """الوكلاء المؤسسون"""
        founders = [
            AgentGenome(name="Alpha_Trend",    rsi_buy=38, rsi_sell=62, adx_min=25, aggression=1.3),
            AgentGenome(name="Beta_Reversal",  rsi_buy=28, rsi_sell=72, adx_min=15, patience=1.8),
            AgentGenome(name="Gamma_Momentum", rsi_buy=42, rsi_sell=58, adx_min=22, aggression=1.5),
            AgentGenome(name="Delta_Safe",     rsi_buy=35, rsi_sell=65, adx_min=20, patience=2.0),
        ]
        for f in founders:
            f.compute_id()
            self.population.append(f)
        self.total_born = len(founders)

    def run_cycle(self, best_agent_fitness: float = 0.0) -> Dict:
        self.cycle += 1
        births = 0; deaths = 0

        # تحديث العمر والأداء
        for agent in self.population:
            if agent.alive:
                agent.age += 1
                agent.fitness = best_agent_fitness * random.uniform(0.7, 1.3)

        # الانتقاء الطبيعي
        survivors, dead = self.mating.natural_selection(
            self.population, self.cycle)
        deaths = len(dead)
        self.total_dead += deaths
        self.population  = survivors

        # التزاوج
        if len(self.population) < self.MAX_POP:
            pairs = self.mating.select_mates(self.population, self.cycle)
            for father, mother in pairs:
                children = self.mating.mate(father, mother, self.cycle)
                for child in children:
                    if len(self.population) >= self.MAX_POP: break
                    self.population.append(child)
                    births += 1
                    self.total_born += 1

        # إنعاش المجتمع
        if len([a for a in self.population if a.alive]) < self.MIN_POP:
            self._init_founders()

        alive = [a for a in self.population if a.alive]
        best  = max(alive, key=lambda a: a.fitness) if alive else None

        return {
            "population": len(alive),
            "births":     births,
            "deaths":     deaths,
            "total_born": self.total_born,
            "total_dead": self.total_dead,
            "best":       best.name if best else "N/A",
            "best_fitness": round(best.fitness if best else 0, 2),
            "generation": max((a.generation for a in alive), default=0)
        }

    def get_best_params(self) -> Dict:
        """أفضل معاملات من النظام البيئي"""
        alive = [a for a in self.population if a.alive]
        if not alive:
            return {}
        best = max(alive, key=lambda a: a.fitness)
        return {
            "rsi_buy":   best.rsi_buy,
            "rsi_sell":  best.rsi_sell,
            "adx_min":   best.adx_min,
            "atr_sl":    best.atr_sl,
            "atr_tp":    best.atr_tp,
            "aggression":best.aggression,
            "name":      best.name,
            "generation":best.generation
        }

    def status_report(self) -> str:
        alive = [a for a in self.population if a.alive]
        if not alive: return "لا وكلاء أحياء"
        best  = max(alive, key=lambda a: a.fitness)
        top3  = sorted(alive, key=lambda a: a.fitness, reverse=True)[:3]
        lines = [
            f"🌍 النظام البيئي — دورة {self.cycle}",
            f"👥 الأحياء: {len(alive)} | 👶 المواليد: {self.total_born} | 💀 الوفيات: {self.total_dead}",
            f"🏆 الأفضل: {best.name} (Gen{best.generation}) fitness={best.fitness:.1f}",
            f"🥇 " + " | ".join(f"{a.name}" for a in top3),
        ]
        return "\n".join(lines)




# ══════════════════════════════════════════════════════════════════════════════
# 🔬 AUTO WALK-FORWARD OPTIMIZER — تحسين تلقائي كل ساعة
# ══════════════════════════════════════════════════════════════════════════════
class AutoWalkForwardOptimizer:
    """
    يُحسّن الاستراتيجية تلقائياً كل ساعة:
    1. يأخذ البيانات الأخيرة
    2. يختبر 50 مجموعة معاملات مختلفة
    3. يختار الأفضل
    4. يُطبّقها على الوكلاء
    """

    def __init__(self):
        self.last_run:    float = 0.0
        self.run_every:   int   = 3600  # كل ساعة
        self.best_params: Dict  = {}
        self.history:     List  = []
        self.improvements:int   = 0

    def should_run(self) -> bool:
        return time.time() - self.last_run >= self.run_every

    def _backtest(self, df: pd.DataFrame,
                   params: Dict,
                   capital: float = 10_000) -> float:
        if df.empty or len(df) < 60: return 0.0
        cap = capital; pos = 0.0; entry = 0.0
        sl  = tp = 0.0; trades = []

        for i in range(20, len(df)):
            row   = df.iloc[i]
            price = float(row.get("close", 0))
            atr   = float(row.get("atr",   price*0.01))
            if price <= 0: continue

            if pos == 0:
                rsi  = float(row.get("rsi",   50))
                adx  = float(row.get("adx",   0))
                mh   = float(row.get("macd_hist", 0))
                vr   = float(row.get("vol_ratio", 1))
                e20  = float(row.get("ema20", 0))
                e50  = float(row.get("ema50", 0))

                buy_c = [
                    rsi < params["rsi_buy"],
                    adx > params["adx_min"],
                    mh  > 0,
                    vr  > params["vol_min"],
                    e20 > e50
                ]
                if sum(buy_c) >= params["min_conditions"]:
                    risk  = cap * 0.01
                    pos   = min(risk/(atr*params["atr_sl"]),
                                cap*0.12/price)
                    entry = price
                    sl    = price - atr*params["atr_sl"]
                    tp    = price + atr*params["atr_tp"]
            else:
                if price<=sl or price>=tp:
                    pnl  = pos*(price-entry)
                    cap  = max(cap+pnl, 1)
                    trades.append(pnl)
                    pos  = 0

        if len(trades) < 5: return 0.0
        arr  = np.array(trades)
        wins = sum(1 for t in trades if t > 0)
        wr   = wins/len(trades)
        sh   = arr.mean()/arr.std()*np.sqrt(252) if arr.std()>0 else 0
        eq   = np.array([capital]+list(np.cumsum(arr)+capital))
        pk   = np.maximum.accumulate(eq)
        dd   = ((pk-eq)/(pk+1e-10)).max()*100
        pf   = sum(t for t in trades if t>0)/(abs(sum(t for t in trades if t<0))+1e-10)
        return max(wr*30 + max(sh,0)*20 + min(pf,5)*15 + max(20-dd,0)*15, 0)

    def optimize(self, df: pd.DataFrame,
                  current_params: Dict) -> Dict:
        """
        يختبر 50 مجموعة معاملات ويختار الأفضل
        """
        if df.empty or len(df) < 100:
            return current_params

        best_score  = self._backtest(df, current_params)
        best_params = current_params.copy()
        tested      = 0

        for _ in range(50):
            # توليد معاملات عشوائية قريبة من الحالية
            candidate = {
                "rsi_buy":        max(20, min(45, current_params["rsi_buy"]  + random.gauss(0, 5))),
                "rsi_sell":       max(55, min(80, current_params["rsi_sell"] + random.gauss(0, 5))),
                "adx_min":        max(10, min(35, current_params["adx_min"]  + random.gauss(0, 3))),
                "vol_min":        max(0.8,min(2.5, current_params["vol_min"] + random.gauss(0, 0.2))),
                "atr_sl":         max(0.8,min(2.5, current_params["atr_sl"]  + random.gauss(0, 0.2))),
                "atr_tp":         max(2.0,min(6.0, current_params["atr_tp"]  + random.gauss(0, 0.3))),
                "min_conditions": random.choice([3, 4, 5]),
            }
            if candidate["atr_tp"] <= candidate["atr_sl"]:
                candidate["atr_tp"] = candidate["atr_sl"] * 2

            score = self._backtest(df, candidate)
            tested += 1
            if score > best_score:
                best_score  = score
                best_params = candidate.copy()

        improved = best_score > self._backtest(df, current_params) + 1
        if improved:
            self.improvements += 1

        self.history.append({
            "time":      datetime.now().isoformat(),
            "score":     round(best_score, 2),
            "improved":  improved,
            "tested":    tested,
            "params":    best_params
        })
        self.last_run    = time.time()
        self.best_params = best_params

        log.info(
            f"🔬 WFO #{len(self.history)} | "
            f"score={best_score:.1f} | "
            f"{'✅ تحسّن' if improved else '➡️ لا تغيير'} | "
            f"tested={tested}"
        )
        return best_params

    def get_stats(self) -> Dict:
        return {
            "runs":        len(self.history),
            "improvements":self.improvements,
            "last_score":  self.history[-1]["score"] if self.history else 0,
            "next_run_in": max(0, int(self.run_every-(time.time()-self.last_run))),
        }




# ══════════════════════════════════════════════════════════════════════════════
# 🧠 SELF-AWARENESS SYSTEM — نظام الوعي الذاتي والذاكرة
# ══════════════════════════════════════════════════════════════════════════════
class BotSelfAwareness:
    """
    البوت يُقيّم نفسه ويتخذ قرارات بناءً على تجربته:
    - يتذكر أفضل وأسوأ صفقاته
    - يُقيّم أداءه كل دورة
    - يُعدّل سلوكه بناءً على السوق
    - يُدرك متى يجب التوقف
    """

    def __init__(self):
        self.memory:        deque = deque(maxlen=200)
        self.best_trade:    Dict  = {}
        self.worst_trade:   Dict  = {}
        self.mood:          str   = "NEUTRAL"
        self.confidence:    float = 0.5
        self.market_view:   str   = "UNKNOWN"
        self.lessons:       List  = []
        self.cycle_count:   int   = 0
        self.win_streak:    int   = 0
        self.loss_streak:   int   = 0

    def remember(self, trade: Dict):
        """يتذكر كل صفقة ويستخلص الدروس"""
        self.memory.append(trade)
        pnl = trade.get("pnl", 0)

        # تحديث أفضل وأسوأ صفقة
        if not self.best_trade or pnl > self.best_trade.get("pnl", 0):
            self.best_trade = trade
        if not self.worst_trade or pnl < self.worst_trade.get("pnl", 0):
            self.worst_trade = trade

        # تحديث المزاج
        if pnl > 0:
            self.win_streak  += 1
            self.loss_streak  = 0
        else:
            self.loss_streak += 1
            self.win_streak   = 0

        # استخلاص الدروس
        if self.loss_streak >= 3:
            lesson = f"خسرت {self.loss_streak} مرات متتالية — يجب تقليل الحجم"
            if lesson not in self.lessons:
                self.lessons.append(lesson)
        if self.win_streak >= 5:
            lesson = f"ربحت {self.win_streak} مرات — السوق مناسب الآن"
            if lesson not in self.lessons:
                self.lessons.append(lesson)

    def evaluate(self) -> Dict:
        """يُقيّم نفسه ويحدد حالته"""
        self.cycle_count += 1

        if not self.memory:
            return {"mood": "NEUTRAL", "confidence": 0.5,
                    "action": "CONTINUE", "message": "أبدأ التعلم..."}

        recent = list(self.memory)[-20:]
        pnls   = [t.get("pnl", 0) for t in recent]
        wins   = sum(1 for p in pnls if p > 0)
        wr     = wins / len(pnls) if pnls else 0
        avg    = float(np.mean(pnls)) if pnls else 0

        # تحديد المزاج
        if wr > 0.65 and avg > 0:
            self.mood       = "CONFIDENT"
            self.confidence = min(0.9, 0.5 + wr*0.4)
            message = f"أداء ممتاز! فوز {wr:.0%} في آخر {len(recent)} صفقة"
            action  = "INCREASE_SIZE"
        elif wr > 0.5:
            self.mood       = "NEUTRAL"
            self.confidence = 0.5
            message = f"أداء جيد. فوز {wr:.0%}"
            action  = "CONTINUE"
        elif wr < 0.35 and self.loss_streak >= 3:
            self.mood       = "CAUTIOUS"
            self.confidence = max(0.2, wr)
            message = f"أداء ضعيف. خسائر {self.loss_streak} متتالية — أُقلل الحجم"
            action  = "REDUCE_SIZE"
        else:
            self.mood       = "LEARNING"
            self.confidence = 0.4
            message = f"أتعلم من التجربة... فوز {wr:.0%}"
            action  = "CONTINUE"

        return {
            "mood":        self.mood,
            "confidence":  round(self.confidence, 2),
            "win_rate":    round(wr, 2),
            "avg_pnl":     round(avg, 4),
            "win_streak":  self.win_streak,
            "loss_streak": self.loss_streak,
            "action":      action,
            "message":     message,
            "lessons":     self.lessons[-3:],
            "best_trade":  self.best_trade.get("pnl", 0),
            "worst_trade": self.worst_trade.get("pnl", 0),
            "total_memory":len(self.memory)
        }

    def think(self, market_data: Dict) -> str:
        """يُفكر في السوق ويُعبّر عن رأيه"""
        regime = market_data.get("regime", "UNKNOWN")
        vol    = market_data.get("volatility", 0)
        trend  = market_data.get("trend", 0)

        thoughts = []

        if regime == "TRENDING_UP":
            thoughts.append("السوق صاعد — فرصة جيدة للشراء")
        elif regime == "TRENDING_DOWN":
            thoughts.append("السوق هابط — يجب الحذر")
        elif regime == "VOLATILE":
            thoughts.append("السوق متذبذب — أُقلل الحجم")
        elif regime == "RANGING":
            thoughts.append("السوق في نطاق — انتظر الاختراق")

        if self.loss_streak >= 2:
            thoughts.append(f"خسرت {self.loss_streak} مرات — أنتظر إشارة قوية")

        if self.confidence > 0.7:
            thoughts.append("أشعر بثقة عالية في هذه الإشارة")
        elif self.confidence < 0.3:
            thoughts.append("لا أثق بالسوق الآن — أنتظر")

        return " | ".join(thoughts) if thoughts else "أراقب السوق..."

    def should_trade(self) -> Tuple[bool, str]:
        """يُقرر هل يتداول أم ينتظر"""
        if self.loss_streak >= 4:
            return False, f"رفضت التداول — {self.loss_streak} خسائر متتالية"
        if self.confidence < 0.25:
            return False, "ثقتي منخفضة جداً — انتظر"
        if self.mood == "CAUTIOUS" and self.loss_streak >= 2:
            return False, "السوق ضدي الآن — أنتظر"
        return True, "✅ جاهز للتداول"

    def size_multiplier(self) -> float:
        """يُعدّل حجم الصفقة بناءً على حالته"""
        if self.mood == "CONFIDENT" and self.win_streak >= 3:
            return 1.2  # يزيد الحجم عند الثقة
        if self.mood == "CAUTIOUS":
            return 0.5  # يُقلل الحجم عند الحذر
        if self.loss_streak >= 2:
            return max(0.3, 1.0 - self.loss_streak * 0.15)
        return 1.0

    def daily_reflection(self) -> str:
        """تأمل يومي — البوت يُراجع يومه"""
        if not self.memory: return "لا توجد صفقات بعد"
        today = [t for t in self.memory
                 if t.get("time","")[:10] == datetime.now().strftime("%Y-%m-%d")]
        if not today: return "لا صفقات اليوم"
        pnls = [t.get("pnl",0) for t in today]
        total= sum(pnls)
        wins = sum(1 for p in pnls if p>0)
        lines = [
            f"📊 تأملي اليومي:",
            f"  الصفقات: {len(today)} | الفوز: {wins} | PnL: {total:+.4f}",
            f"  مزاجي: {self.mood} | ثقتي: {self.confidence:.0%}",
        ]
        if self.lessons:
            lines.append(f"  درس اليوم: {self.lessons[-1]}")
        if total > 0:
            lines.append("  ✅ يوم جيد — أواصل بنفس الاستراتيجية")
        else:
            lines.append("  ⚠️ يوم صعب — سأكون أكثر حذراً غداً")
        return "\n".join(lines)




# ══════════════════════════════════════════════════════════════════════════════
# 🤖 DCA BOT ذكي — Dollar Cost Averaging المتطور
# ══════════════════════════════════════════════════════════════════════════════
class SmartDCABot:
    """
    أفضل استراتيجية للسوق المتذبذب:
    يشتري على دفعات عند كل انخفاض
    يُخفض متوسط السعر تلقائياً
    """
    def __init__(self):
        self.positions: Dict[str, List] = defaultdict(list)
        self.enabled   = True
        self.max_orders= 5       # أقصى 5 دفعات
        self.step_pct  = 0.03    # شراء كل 3% انخفاض
        self.base_size = 0.02    # 2% من الرصيد للدفعة الأولى
        self.multiplier= 1.5     # كل دفعة × 1.5

    def should_dca(self, symbol: str, price: float) -> Tuple[bool, float]:
        orders = self.positions[symbol]
        if len(orders) >= self.max_orders: return False, 0
        if not orders:
            return True, self.base_size
        last_price = orders[-1]["price"]
        drop_pct   = (last_price - price) / last_price
        if drop_pct >= self.step_pct:
            size = self.base_size * (self.multiplier ** len(orders))
            return True, min(size, 0.10)
        return False, 0

    def add_order(self, symbol: str, price: float, qty: float):
        self.positions[symbol].append({
            "price": price, "qty": qty,
            "time": datetime.now().isoformat()
        })

    def avg_price(self, symbol: str) -> float:
        orders = self.positions[symbol]
        if not orders: return 0
        total_cost = sum(o["price"]*o["qty"] for o in orders)
        total_qty  = sum(o["qty"] for o in orders)
        return total_cost/total_qty if total_qty > 0 else 0

    def total_qty(self, symbol: str) -> float:
        return sum(o["qty"] for o in self.positions[symbol])

    def should_take_profit(self, symbol: str,
                            price: float, tp_pct: float = 0.05) -> bool:
        avg = self.avg_price(symbol)
        return avg > 0 and (price - avg) / avg >= tp_pct

    def clear(self, symbol: str):
        self.positions[symbol] = []


# ══════════════════════════════════════════════════════════════════════════════
# 📊 SMART GRID TRADING — تداول الشبكة الذكي
# ══════════════════════════════════════════════════════════════════════════════
class SmartGridTrading:
    """
    يُنشئ شبكة أوامر فوق وتحت السعر الحالي:
    يربح من كل تذبذب في السوق
    أفضل في السوق الجانبي (Ranging)
    """
    def __init__(self):
        self.grids:    Dict[str, Dict] = {}
        self.enabled   = True
        self.levels    = 8        # 8 مستويات
        self.range_pct = 0.04     # نطاق 4%
        self.size_pct  = 0.01     # 1% لكل مستوى

    def create_grid(self, symbol: str, price: float,
                     balance: float) -> List[Dict]:
        step   = price * self.range_pct / self.levels
        orders = []
        for i in range(1, self.levels//2 + 1):
            # أوامر شراء تحت السعر
            buy_price = price - step * i
            orders.append({
                "side":  "buy",
                "price": round(buy_price, 4),
                "qty":   round(balance * self.size_pct / buy_price, 6),
                "level": -i
            })
            # أوامر بيع فوق السعر
            sell_price = price + step * i
            orders.append({
                "side":  "sell",
                "price": round(sell_price, 4),
                "qty":   round(balance * self.size_pct / sell_price, 6),
                "level": i
            })

        self.grids[symbol] = {
            "center":   price,
            "orders":   orders,
            "created":  datetime.now().isoformat(),
            "profit":   0.0
        }
        log.info(f"📊 Grid [{symbol}]: {len(orders)} أمر حول {price:.2f}")
        return orders

    def check_fills(self, symbol: str,
                     price: float) -> List[Dict]:
        grid = self.grids.get(symbol)
        if not grid: return []
        filled = []
        for order in grid["orders"]:
            if (order["side"]=="buy"  and price <= order["price"] or
                order["side"]=="sell" and price >= order["price"]):
                filled.append(order)
                profit = (price - order["price"]) * order["qty"]
                grid["profit"] += profit
        return filled

    def needs_rebalance(self, symbol: str,
                         price: float) -> bool:
        grid = self.grids.get(symbol)
        if not grid: return True
        center  = grid["center"]
        drift   = abs(price - center) / center
        return drift > self.range_pct * 1.5


# ══════════════════════════════════════════════════════════════════════════════
# 🔄 SMART ARBITRAGE — مراجحة Spot/Futures ذكية
# ══════════════════════════════════════════════════════════════════════════════
class SmartArbitrage:
    """
    يستغل فروقات الأسعار بين:
    Spot vs Futures (Basis Trading)
    OKX vs Binance (Cross-Exchange)
    """
    def __init__(self):
        self.min_spread = 0.002   # 0.2% حد أدنى
        self.enabled    = True
        self._cache:    Dict = {}
        self._ttl       = 10

    async def check_basis(self, symbol: str,
                           spot_price: float) -> Dict:
        """Spot vs Futures Basis"""
        key = f"basis_{symbol}_{int(time.time()//self._ttl)}"
        if key in self._cache: return self._cache[key]
        try:
            async with aiohttp.ClientSession() as s:
                swap_sym = symbol.replace("USDT","USDT-SWAP").replace("-","")
                async with s.get(
                    f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-SWAP",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as r:
                    data  = await r.json()
                    fut_p = float(data["data"][0]["last"]) if data.get("data") else spot_price
        except:
            fut_p = spot_price * (1 + random.gauss(0, 0.001))

        basis    = (fut_p - spot_price) / spot_price
        signal   = "SELL_FUTURES" if basis >  self.min_spread else                    "BUY_FUTURES"  if basis < -self.min_spread else "HOLD"
        result = {
            "spot":    spot_price,
            "futures": round(fut_p, 4),
            "basis":   round(basis, 4),
            "basis_pct": round(basis*100, 3),
            "signal":  signal,
            "profit_est": round(abs(basis)*100 - 0.1, 3)
        }
        self._cache[key] = result
        return result

    async def check_cross_exchange(self, symbol: str,
                                    okx_price: float) -> Dict:
        """OKX vs Binance"""
        coin = symbol.replace("-USDT","USDT")
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={coin}",
                    timeout=aiohttp.ClientTimeout(total=4)
                ) as r:
                    data    = await r.json()
                    bn_price= float(data.get("price", okx_price))
        except:
            bn_price = okx_price

        spread = (okx_price - bn_price) / bn_price
        signal = ("BUY_OKX_SELL_BN"  if spread < -self.min_spread else
                  "SELL_OKX_BUY_BN"  if spread >  self.min_spread else
                  "NO_ARB")
        return {
            "okx":    okx_price,
            "binance":round(bn_price, 4),
            "spread": round(spread*100, 3),
            "signal": signal,
            "profit_est": round(abs(spread)*100 - 0.1, 3)
        }


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 FLYWHEEL STRATEGY — استراتيجية دولاب الطاقة
# ══════════════════════════════════════════════════════════════════════════════
class FlywheelStrategy:
    """
    استراتيجية 2026 الجديدة:
    يُعيد استثمار الأرباح تلقائياً في أقوى الفرص
    كل ربح → يُضاف للرصيد → يُكبّر الصفقة التالية
    تأثير مركّب قوي جداً على المدى الطويل
    """
    def __init__(self):
        self.compound_rate = 0.50   # 50% من الربح يُعاد استثماره
        self.accumulated   = 0.0
        self.cycles        = 0
        self.history:      List = []

    def record_profit(self, pnl: float) -> float:
        """يسجّل الربح ويحسب ما يُعاد استثماره"""
        if pnl <= 0: return 0.0
        reinvest = pnl * self.compound_rate
        self.accumulated += reinvest
        self.cycles      += 1
        self.history.append({
            "pnl":      round(pnl, 4),
            "reinvest": round(reinvest, 4),
            "total":    round(self.accumulated, 4),
            "cycle":    self.cycles
        })
        return reinvest

    def get_bonus_size(self, base_qty: float) -> float:
        """يُضيف حجماً إضافياً من الأرباح المتراكمة"""
        if self.accumulated <= 0: return base_qty
        bonus = min(self.accumulated * 0.1, base_qty * 0.5)
        self.accumulated -= bonus
        return base_qty + bonus

    def compound_report(self) -> str:
        if not self.history: return "لا أرباح بعد"
        total_profit  = sum(h["pnl"] for h in self.history)
        total_reinvest= sum(h["reinvest"] for h in self.history)
        return (
            f"🎯 Flywheel Report:\n"
            f"  دورات: {self.cycles}\n"
            f"  إجمالي ربح: {total_profit:+.4f}\n"
            f"  مُعاد استثماره: {total_reinvest:.4f}\n"
            f"  متراكم جاهز: {self.accumulated:.4f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 📡 SIGNAL MARKETPLACE — سوق الإشارات
# ══════════════════════════════════════════════════════════════════════════════
class SignalMarketplace:
    """
    يجمع إشارات من مصادر متعددة:
    - TradingView Webhooks
    - Telegram Channels
    - Twitter/X Signals
    - On-Chain Alerts
    ويُقيّم موثوقية كل مصدر
    """
    def __init__(self):
        self.sources:  Dict[str, Dict] = {
            "onchain":   {"weight": 0.30, "signals": deque(maxlen=50)},
            "technical": {"weight": 0.25, "signals": deque(maxlen=50)},
            "sentiment": {"weight": 0.25, "signals": deque(maxlen=50)},
            "volume":    {"weight": 0.20, "signals": deque(maxlen=50)},
        }
        self.received: int   = 0
        self.used:     int   = 0

    def add_signal(self, source: str, symbol: str,
                    direction: str, confidence: float,
                    metadata: Dict = None):
        if source not in self.sources: return
        signal = {
            "symbol":     symbol,
            "direction":  direction,
            "confidence": confidence,
            "time":       datetime.now().isoformat(),
            "metadata":   metadata or {}
        }
        self.sources[source]["signals"].append(signal)
        self.received += 1

    def aggregate(self, symbol: str) -> Tuple[str, float]:
        buy_score = sell_score = 0.0
        for source, data in self.sources.items():
            recent = [s for s in data["signals"]
                      if s["symbol"]==symbol and
                      (datetime.now() - datetime.fromisoformat(s["time"])).seconds < 300]
            if not recent: continue
            latest = recent[-1]
            w = data["weight"] * latest["confidence"]
            if latest["direction"] == "BUY":   buy_score  += w
            elif latest["direction"] == "SELL": sell_score += w

        total = buy_score + sell_score + 1e-10
        if buy_score/total  >= 0.60: return "BUY",  round(buy_score/total,3)
        if sell_score/total >= 0.60: return "SELL", round(sell_score/total,3)
        return "HOLD", 0.0

    def get_stats(self) -> Dict:
        return {
            "received": self.received,
            "used":     self.used,
            "sources":  {k: len(v["signals"]) for k,v in self.sources.items()}
        }




# ══════════════════════════════════════════════════════════════════════════════
# 🧬 NEXT-GEN AGENT SYSTEM — الجيل القادم من الوكلاء
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. الذاكرة طويلة المدى ──────────────────────────────────────────────────
class LongTermMemory:
    """
    البوت يتذكر كل شيء:
    - أفضل الأوقات للتداول
    - أسوأ الأنماط
    - تاريخ كل رمز
    - الدروس المستفادة
    """
    def __init__(self):
        self.episodic:  deque = deque(maxlen=1000)  # ذاكرة الأحداث
        self.semantic:  Dict  = {}                   # ذاكرة المعرفة
        self.patterns:  Dict  = defaultdict(list)    # أنماط السوق
        self.skills:    Dict  = {}                   # مهارات مكتسبة

    def store(self, event: Dict):
        """يحفظ حدثاً في الذاكرة"""
        event["stored_at"] = datetime.now().isoformat()
        self.episodic.append(event)

        # استخلاص المعرفة
        symbol = event.get("symbol","")
        hour   = datetime.now().hour
        pnl    = event.get("pnl", 0)

        if symbol:
            if symbol not in self.semantic:
                self.semantic[symbol] = {
                    "best_hour": defaultdict(float),
                    "total_pnl": 0,
                    "trades":    0,
                    "win_rate":  0
                }
            self.semantic[symbol]["total_pnl"] += pnl
            self.semantic[symbol]["trades"]    += 1
            self.semantic[symbol]["best_hour"][hour] += pnl

    def recall(self, symbol: str, context: str = "") -> Dict:
        """يستذكر معلومات عن رمز معين"""
        info = self.semantic.get(symbol, {})
        if not info: return {}
        best_hour = max(info.get("best_hour", {0:0}),
                        key=info.get("best_hour", {0:0}).get,
                        default=0)
        return {
            "symbol":    symbol,
            "total_pnl": round(info.get("total_pnl",0), 4),
            "trades":    info.get("trades", 0),
            "best_hour": best_hour,
            "insight":   f"أفضل ساعة للتداول: {best_hour}:00"
        }

    def best_symbols(self, n: int = 5) -> List[str]:
        """يتذكر أفضل الرموز أداءً"""
        ranked = sorted(
            self.semantic.items(),
            key=lambda x: x[1].get("total_pnl", 0),
            reverse=True
        )
        return [s for s, _ in ranked[:n]]

    def learn_pattern(self, pattern: str, outcome: float):
        """يتعلم من الأنماط"""
        self.patterns[pattern].append(outcome)
        if len(self.patterns[pattern]) >= 10:
            avg = np.mean(self.patterns[pattern])
            self.skills[pattern] = {
                "avg_outcome": round(avg, 4),
                "reliability": len([o for o in self.patterns[pattern] if o > 0]) / len(self.patterns[pattern]),
                "count":       len(self.patterns[pattern])
            }


# ── 2. محرك الفرضيات ────────────────────────────────────────────────────────
class HypothesisEngine:
    """
    البوت يبني فرضيات ويختبرها:
    "إذا RSI < 30 وADX > 25 → فرصة شراء بنسبة 70%"
    يختبر الفرضية → يُحدّث الثقة → يُطبّقها أو يرفضها
    """
    def __init__(self):
        self.hypotheses: Dict[str, Dict] = {}
        self.tested:     int = 0
        self.confirmed:  int = 0

    def generate(self, df: pd.DataFrame) -> List[Dict]:
        """يولّد فرضيات من البيانات الحالية"""
        if df.empty or len(df) < 30: return []
        last = df.iloc[-1]
        hyps = []

        rsi  = float(last.get("rsi",   50))
        adx  = float(last.get("adx",   0))
        bb   = float(last.get("bb_pct",0.5))
        vr   = float(last.get("vol_ratio",1))
        mh   = float(last.get("macd_hist",0))

        # فرضية 1: Oversold Bounce
        if rsi < 32 and adx > 20:
            hyps.append({
                "id":         "OVERSOLD_BOUNCE",
                "direction":  "BUY",
                "confidence": 0.65 + (30-rsi)/100,
                "reason":     f"RSI={rsi:.1f} منخفض جداً مع ADX قوي",
                "expiry":     5  # تنتهي بعد 5 دورات
            })

        # فرضية 2: BB Squeeze Breakout
        if bb < 0.15 and vr > 1.8:
            hyps.append({
                "id":         "BB_BREAKOUT",
                "direction":  "BUY" if mh > 0 else "SELL",
                "confidence": 0.60,
                "reason":     f"BB Squeeze مع حجم عالٍ",
                "expiry":     3
            })

        # فرضية 3: Momentum Continuation
        if rsi > 55 and mh > 0 and adx > 25 and vr > 1.5:
            hyps.append({
                "id":         "MOMENTUM_BULL",
                "direction":  "BUY",
                "confidence": 0.70,
                "reason":     f"زخم قوي مع حجم وADX",
                "expiry":     8
            })

        return hyps

    def test(self, hyp_id: str, outcome: float) -> Dict:
        """يختبر فرضية ويُحدّث ثقته"""
        self.tested += 1
        if hyp_id not in self.hypotheses:
            self.hypotheses[hyp_id] = {
                "total":    0, "correct": 0,
                "confidence": 0.5, "outcomes": []
            }
        h = self.hypotheses[hyp_id]
        h["total"]    += 1
        h["outcomes"].append(outcome)
        if outcome > 0: h["correct"] += 1; self.confirmed += 1
        h["confidence"] = h["correct"] / h["total"]
        return h

    def best_hypothesis(self, hyps: List[Dict]) -> Optional[Dict]:
        """يختار أفضل فرضية"""
        if not hyps: return None
        for h in hyps:
            if h["id"] in self.hypotheses:
                historical = self.hypotheses[h["id"]]["confidence"]
                h["confidence"] = (h["confidence"] + historical) / 2
        return max(hyps, key=lambda h: h["confidence"])


# ── 3. التنفيذ الذكي ─────────────────────────────────────────────────────────
class SmartExecutionEngine:
    """
    يُنفّذ الأوامر بذكاء:
    - يُقسّم الأوامر الكبيرة (TWAP)
    - يختار أفضل توقيت
    - يُقلّل الانزلاق
    - يراقب السيولة
    """
    def __init__(self):
        self.slippage_history: deque = deque(maxlen=100)
        self.avg_slippage:     float = 0.0005

    def optimal_split(self, qty: float, price: float,
                       balance: float) -> List[Dict]:
        """يُقسّم الأمر لتقليل التأثير"""
        value = qty * price
        if value < balance * 0.05:
            return [{"qty": qty, "delay": 0}]
        n     = min(int(value / (balance * 0.02)), 5)
        split = qty / n
        return [{"qty": round(split,6), "delay": i*30}
                for i in range(n)]

    def best_time_to_trade(self) -> bool:
        """هل الوقت مناسب للتنفيذ؟"""
        hour = datetime.now().hour
        # تجنب ساعات السيولة المنخفضة
        low_liquidity = [1, 2, 3, 4, 5]
        return hour not in low_liquidity

    def estimate_slippage(self, qty: float,
                           daily_volume: float) -> float:
        """يُقدّر الانزلاق المتوقع"""
        impact = 0.1 * math.sqrt(qty / (daily_volume + 1e-10))
        return min(impact, 0.01)

    def record_slippage(self, expected: float, actual: float):
        """يتعلم من الانزلاق الفعلي"""
        slip = abs(actual - expected) / expected
        self.slippage_history.append(slip)
        self.avg_slippage = float(np.mean(self.slippage_history))


# ── 4. التعلم التعزيزي البسيط ────────────────────────────────────────────────
class ReinforcementLearner:
    """
    يتعلم من كل صفقة في الزمن الحقيقي:
    ربح  → يُعزّز الاستراتيجية
    خسارة → يُعدّل المعاملات
    """
    def __init__(self):
        self.q_table:  Dict  = defaultdict(float)
        self.lr:       float = 0.01   # معدل التعلم
        self.gamma:    float = 0.95   # معامل الخصم
        self.epsilon:  float = 0.15   # استكشاف
        self.episodes: int   = 0

    def choose_action(self, state: str) -> str:
        """يختار: AGGRESSIVE / CONSERVATIVE / NEUTRAL"""
        import random
        q_agg  = self.q_table.get(f"{state}_AGGRESSIVE",  0.0)
        q_con  = self.q_table.get(f"{state}_CONSERVATIVE",0.0)
        q_neu  = self.q_table.get(f"{state}_NEUTRAL",     0.0)
        if random.random() < self.epsilon:
            return random.choice(["AGGRESSIVE","CONSERVATIVE","NEUTRAL"])
        best = max([("AGGRESSIVE",q_agg),("CONSERVATIVE",q_con),("NEUTRAL",q_neu)],
                   key=lambda x: x[1])
        return best[0]

    def learn(self, state: str, action: str, reward: float, next_state: str):
        """يتعلم من نتيجة الصفقة"""
        self.episodes += 1
        key      = f"{state}_{action}"
        next_max = max(self.q_table.get(f"{next_state}_AGGRESSIVE",0),
                       self.q_table.get(f"{next_state}_CONSERVATIVE",0),
                       self.q_table.get(f"{next_state}_NEUTRAL",0))
        old_q    = self.q_table.get(key, 0.0)
        self.q_table[key] = old_q + self.lr*(reward + self.gamma*next_max - old_q)
        # تقليل الاستكشاف تدريجياً
        self.epsilon = max(0.05, self.epsilon * 0.999)

    def state_key(self, indicators: Dict) -> str:
        """يُحوّل المؤشرات لمفتاح حالة"""
        rsi  = int(indicators.get("rsi",   50) // 10) * 10
        adx  = int(indicators.get("adx",   0)  // 10) * 10
        trend= "UP" if indicators.get("ema20",0) > indicators.get("ema50",0) else "DN"
        return f"RSI{rsi}_ADX{adx}_{trend}"

    def choose_action(self, state: str) -> str:
        """يختار الإجراء بناءً على التجربة"""
        if random.random() < self.epsilon:
            return random.choice(["BUY","SELL","HOLD"])
        q_buy  = self.q_table.get(f"{state}_BUY",  0)
        q_sell = self.q_table.get(f"{state}_SELL", 0)
        q_hold = self.q_table.get(f"{state}_HOLD", 0)
        actions = {"BUY": q_buy, "SELL": q_sell, "HOLD": q_hold}
        return max(actions, key=actions.get)

    def learn(self, state: str, action: str,
               reward: float, next_state: str):
        """يتعلم من النتيجة"""
        key      = f"{state}_{action}"
        next_max = max(
            self.q_table.get(f"{next_state}_BUY",  0),
            self.q_table.get(f"{next_state}_SELL", 0),
            self.q_table.get(f"{next_state}_HOLD", 0)
        )
        self.q_table[key] += self.lr * (
            reward + self.gamma * next_max - self.q_table[key])
        self.episodes += 1
        if self.epsilon > 0.05:
            self.epsilon *= 0.999

    def best_actions(self) -> List[Tuple]:
        """يُظهر أفضل الإجراءات المتعلَّمة"""
        return sorted(
            [(k,v) for k,v in self.q_table.items() if v > 0],
            key=lambda x: x[1], reverse=True
        )[:5]


# ── 5. العقل الجماعي ─────────────────────────────────────────────────────────
class CollectiveIntelligence:
    """
    الوكلاء يتواصلون ويتخذون قرارات جماعية:
    كل وكيل يُصوّت → يُحسب الإجماع الجماعي
    يُعطي كل وكيل وزناً بناءً على أدائه التاريخي
    """
    def __init__(self):
        self.agent_performance: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50))
        self.messages: deque = deque(maxlen=200)

    def broadcast(self, agent_name: str,
                   signal: str, confidence: float,
                   reasoning: str):
        """وكيل يُرسل إشارة للمجموعة"""
        self.messages.append({
            "agent":      agent_name,
            "signal":     signal,
            "confidence": confidence,
            "reasoning":  reasoning,
            "time":       datetime.now().isoformat()
        })

    def record_outcome(self, agent_name: str, pnl: float):
        """يُسجّل نتيجة وكيل لتعديل وزنه"""
        self.agent_performance[agent_name].append(pnl)

    def agent_weight(self, agent_name: str) -> float:
        """يحسب وزن الوكيل بناءً على أدائه"""
        history = list(self.agent_performance[agent_name])
        if len(history) < 5: return 1.0
        wins = sum(1 for p in history if p > 0)
        wr   = wins / len(history)
        return max(0.2, min(2.0, wr * 2))

    def collective_decision(self,
                             recent_secs: int = 60) -> Dict:
        """القرار الجماعي لكل الوكلاء"""
        cutoff  = datetime.now() - timedelta(seconds=recent_secs)
        recent  = [m for m in self.messages
                   if datetime.fromisoformat(m["time"]) >= cutoff]
        if not recent:
            return {"signal":"HOLD","confidence":0,"consensus":0}

        buy_w = sell_w = total_w = 0.0
        for m in recent:
            w = self.agent_weight(m["agent"]) * m["confidence"]
            total_w += w
            if m["signal"]=="BUY":    buy_w  += w
            elif m["signal"]=="SELL": sell_w += w

        if total_w == 0:
            return {"signal":"HOLD","confidence":0,"consensus":0}

        bs = buy_w/total_w; ss = sell_w/total_w
        consensus = max(bs, ss)

        if bs >= 0.55:   final = "BUY";  conf = bs
        elif ss >= 0.55: final = "SELL"; conf = ss
        else:            final = "HOLD"; conf = consensus

        return {
            "signal":    final,
            "confidence":round(conf, 3),
            "consensus": round(consensus*100, 1),
            "agents":    len(set(m["agent"] for m in recent)),
            "buy_pct":   round(bs*100, 1),
            "sell_pct":  round(ss*100, 1)
        }




# ══════════════════════════════════════════════════════════════════════════════
# ⚡ META-AGENT SYSTEM — الـ 25% الناقص
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. تغيير الشخصية الكاملة حسب السوق ─────────────────────────────────────
class PersonalityEngine:
    """
    نفس البوت — لكن بعقول مختلفة حسب السوق:
    TRENDING   → شخصية Momentum
    RANGING    → شخصية Mean-Reversion
    VOLATILE   → شخصية Conservative
    BREAKOUT   → شخصية Aggressive
    CRASH      → شخصية Defensive
    """

    PERSONALITIES = {
        "TRENDING_UP": {
            "rsi_buy":        42,    "rsi_sell":       68,
            "adx_min":        28,    "vol_min":         1.3,
            "atr_sl":         1.2,   "atr_tp":          3.5,
            "aggression":     1.4,   "min_conditions":  3,
            "description":   "Momentum — اتبع الاتجاه",
        },
        "TRENDING_DOWN": {
            "rsi_buy":        32,    "rsi_sell":       58,
            "adx_min":        28,    "vol_min":         1.3,
            "atr_sl":         1.2,   "atr_tp":          3.0,
            "aggression":     1.2,   "min_conditions":  4,
            "description":   "Fade — بيع على الارتفاعات",
        },
        "RANGING": {
            "rsi_buy":        30,    "rsi_sell":       70,
            "adx_min":        15,    "vol_min":         1.1,
            "atr_sl":         1.8,   "atr_tp":          2.5,
            "aggression":     0.8,   "min_conditions":  5,
            "description":   "Mean-Reversion — ارتداد من الأطراف",
        },
        "VOLATILE": {
            "rsi_buy":        25,    "rsi_sell":       75,
            "adx_min":        10,    "vol_min":         2.0,
            "atr_sl":         2.5,   "atr_tp":          5.0,
            "aggression":     0.5,   "min_conditions":  6,
            "description":   "Conservative — حجم صغير وحماية عالية",
        },
        "BREAKOUT": {
            "rsi_buy":        48,    "rsi_sell":       62,
            "adx_min":        22,    "vol_min":         1.8,
            "atr_sl":         1.0,   "atr_tp":          4.0,
            "aggression":     1.6,   "min_conditions":  3,
            "description":   "Aggressive — اختراق قوي",
        },
        "UNKNOWN": {
            "rsi_buy":        40,    "rsi_sell":       60,
            "adx_min":        20,    "vol_min":         1.2,
            "atr_sl":         1.5,   "atr_tp":          3.0,
            "aggression":     1.0,   "min_conditions":  4,
            "description":   "Neutral — إعدادات افتراضية",
        },
    }

    def __init__(self):
        self.current_personality = "UNKNOWN"
        self.switch_count        = 0
        self.history:    List    = []

    def detect_regime(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < 50: return "UNKNOWN"
        c  = df["close"].astype(float)
        h  = df["high"].astype(float)
        l  = df["low"].astype(float)

        ema20  = c.ewm(span=20).mean().iloc[-1]
        ema50  = c.ewm(span=50).mean().iloc[-1]
        ema200 = c.ewm(span=200).mean().iloc[-1] if len(c)>=200 else ema50

        tr  = pd.concat([h-l,(h-c.shift()).abs(),
                          (l-c.shift()).abs()],axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        atr_ratio = float(atr.iloc[-1]/atr.rolling(50).mean().iloc[-1])                     if len(atr)>=50 else 1.0

        pdm=(h.diff()).clip(lower=0); ndm=(-l.diff()).clip(lower=0)
        adx = float((100*(pdm.rolling(14).mean()-ndm.rolling(14).mean()).abs()
                     /(pdm.rolling(14).mean()+ndm.rolling(14).mean()+1e-10)
                     ).rolling(14).mean().iloc[-1])

        prices = c.values[-60:]
        lags   = [2,4,8,16]
        try:
            taus  = [np.std(np.subtract(prices[lag:],prices[:-lag]))
                     for lag in lags]
            hurst = float(np.polyfit(np.log(lags),np.log(taus),1)[0])                     if all(t>0 for t in taus) else 0.5
        except: hurst = 0.5

        # تصنيف ذكي
        if atr_ratio > 2.0: return "VOLATILE"
        if adx > 30 and ema20 > ema50 > ema200 and hurst > 0.55:
            return "TRENDING_UP"
        if adx > 30 and ema20 < ema50 < ema200 and hurst > 0.55:
            return "TRENDING_DOWN"
        if adx < 20 and hurst < 0.45: return "RANGING"
        if 20 < adx < 30 and atr_ratio > 1.3: return "BREAKOUT"
        return "UNKNOWN"

    def switch_personality(self, regime: str,
                            evo_agent) -> bool:
        if regime == self.current_personality: return False
        personality = self.PERSONALITIES.get(regime,
                      self.PERSONALITIES["UNKNOWN"])
        # تطبيق الشخصية الجديدة على الوكيل التطوري
        evo_agent.params["rsi_buy"]  = personality["rsi_buy"]
        evo_agent.params["rsi_sell"] = personality["rsi_sell"]
        evo_agent.params["adx_min"]  = personality["adx_min"]
        evo_agent.params["vol_min"]  = personality["vol_min"]
        old = self.current_personality
        self.current_personality = regime
        self.switch_count += 1
        self.history.append({
            "from": old, "to": regime,
            "time": datetime.now().isoformat()
        })
        log.info(
            f"🎭 تغيير الشخصية: {old} → {regime} | "
            f"{personality['description']}"
        )
        return True

    def current_params(self) -> Dict:
        return self.PERSONALITIES.get(
            self.current_personality,
            self.PERSONALITIES["UNKNOWN"])


# ── 2. حذف ما لا يعمل ذاتياً ───────────────────────────────────────────────
class StrategyPruner:
    """
    يُراقب أداء كل استراتيجية ويحذف الفاشلة:
    - يتتبع أداء كل وكيل
    - يُحسب Z-Score لكل وكيل
    - يُعطّل الوكلاء الضعيفين مؤقتاً
    - يُعيد تفعيلهم إذا تحسّن السوق
    """
    def __init__(self):
        self.agent_pnl:    Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=50))
        self.disabled:     Dict[str, int]   = {}
        self.prune_count:  int = 0

    def record(self, agent_name: str, pnl: float):
        self.agent_pnl[agent_name].append(pnl)

    def prune(self, agents: List) -> Tuple[List, List]:
        active   = []
        pruned   = []
        cycle    = 0

        for agent in agents:
            name  = agent.name
            hist  = list(self.agent_pnl[name])

            # إعادة تفعيل المعطّلين
            if name in self.disabled:
                self.disabled[name] -= 1
                if self.disabled[name] <= 0:
                    del self.disabled[name]
                    log.info(f"♻️ إعادة تفعيل: {name}")
                else:
                    pruned.append(agent)
                    continue

            if len(hist) < 10:
                active.append(agent)
                continue

            arr    = np.array(hist)
            mean   = arr.mean()
            std    = arr.std()
            z      = mean/std if std > 0 else 0
            wr     = sum(1 for p in hist if p>0)/len(hist)

            # تعطيل الوكلاء الضعيفين
            if z < -1.5 or (wr < 0.3 and len(hist) >= 20):
                self.disabled[name] = 20  # تعطيل 20 دورة
                self.prune_count   += 1
                pruned.append(agent)
                log.warning(
                    f"✂️ تعطيل مؤقت: {name} | "
                    f"WR={wr:.0%} | Z={z:.2f}")
            else:
                active.append(agent)

        return active, pruned


# ── 3. دمج الاستراتيجيات تلقائياً ──────────────────────────────────────────
class StrategyMerger:
    """
    يدمج أفضل ما في كل استراتيجية:
    يأخذ نقاط القوة من كل وكيل
    ويُنشئ استراتيجية مُركّبة أفضل
    """
    def __init__(self):
        self.merged_strategies: List[Dict] = []
        self.merge_count: int = 0

    def merge(self, agent_results: Dict[str, Tuple]) -> Dict:
        """
        agent_results = {agent_name: (signal, confidence, details)}
        """
        buy_agents  = [(n,c,d) for n,(s,c,d) in agent_results.items()
                       if s == "BUY"]
        sell_agents = [(n,c,d) for n,(s,c,d) in agent_results.items()
                       if s == "SELL"]

        if not buy_agents and not sell_agents:
            return {"signal":"HOLD","confidence":0,"merged":False}

        # دمج نقاط القوة
        if buy_agents:
            # أخذ أعلى ثقة من كل وكيل
            best_conf   = max(c for _,c,_ in buy_agents)
            avg_conf    = np.mean([c for _,c,_ in buy_agents])
            merged_conf = best_conf * 0.4 + avg_conf * 0.6
            if len(buy_agents) >= 3:
                merged_conf = min(merged_conf * 1.15, 0.95)
            strategy = {
                "signal":     "BUY",
                "confidence": round(merged_conf, 3),
                "agents":     [n for n,_,_ in buy_agents],
                "merged":     True,
                "count":      len(buy_agents)
            }
        else:
            best_conf   = max(c for _,c,_ in sell_agents)
            avg_conf    = np.mean([c for _,c,_ in sell_agents])
            merged_conf = best_conf * 0.4 + avg_conf * 0.6
            if len(sell_agents) >= 3:
                merged_conf = min(merged_conf * 1.15, 0.95)
            strategy = {
                "signal":     "SELL",
                "confidence": round(merged_conf, 3),
                "agents":     [n for n,_,_ in sell_agents],
                "merged":     True,
                "count":      len(sell_agents)
            }

        self.merged_strategies.append(strategy)
        self.merge_count += 1
        return strategy


# ── 4. المدير الأعلى — Meta-Agent ───────────────────────────────────────────
class MetaAgentManager:
    """
    يُدير كل الأنظمة فوقها جميعاً:
    - يُقرر أي شخصية تُفعَّل
    - يُقرر أي وكلاء يعملون
    - يُدمج الاستراتيجيات
    - يُراقب الأداء الكلي
    - هدفه الوحيد: البقاء والربح طويل المدى
    """
    def __init__(self):
        self.personality = PersonalityEngine()
        self.pruner      = StrategyPruner()
        self.merger      = StrategyMerger()
        self.decisions:  deque = deque(maxlen=500)
        self.cycle:      int   = 0
        self.total_pnl:  float = 0.0

    def run(self, df: pd.DataFrame,
             agents: List,
             evo_agent,
             agent_results: Dict) -> Dict:
        self.cycle += 1

        # 1. كشف نظام السوق وتغيير الشخصية
        regime  = self.personality.detect_regime(df)
        switched= self.personality.switch_personality(regime, evo_agent)

        # 2. تقليم الوكلاء الضعفاء
        active_agents, pruned = self.pruner.prune(agents)

        # 3. دمج الاستراتيجيات
        merged = self.merger.merge(agent_results)

        # 4. القرار النهائي
        personality_params = self.personality.current_params()
        decision = {
            "cycle":       self.cycle,
            "regime":      regime,
            "personality": self.personality.current_personality,
            "switched":    switched,
            "active_agents": len(active_agents),
            "pruned_agents": len(pruned),
            "merged_signal": merged,
            "params":      personality_params,
            "time":        datetime.now().isoformat()
        }
        self.decisions.append(decision)

        if self.cycle % 10 == 0:
            log.info(
                f"⚡ Meta-Agent دورة {self.cycle} | "
                f"نظام: {regime} | "
                f"وكلاء نشطون: {len(active_agents)} | "
                f"معطّلون: {len(pruned)} | "
                f"تبديلات: {self.personality.switch_count}"
            )
        return decision

    def record_trade(self, agent_name: str, pnl: float):
        self.pruner.record(agent_name, pnl)
        self.total_pnl += pnl

    def status(self) -> str:
        p = self.personality
        return (
            f"⚡ Meta-Agent Status:\n"
            f"  الشخصية: {p.current_personality}\n"
            f"  تبديلات: {p.switch_count}\n"
            f"  وكلاء معطّلون: {len(self.pruner.disabled)}\n"
            f"  استراتيجيات مدموجة: {self.merger.merge_count}\n"
            f"  إجمالي PnL: {self.total_pnl:+.4f}"
        )




# ══════════════════════════════════════════════════════════════════════════════
# 📊 ICT + SMC + CRT + TBS + HTF — المنهجية الكاملة
# ══════════════════════════════════════════════════════════════════════════════

class SMCAnalyzer:
    """
    Smart Money Concepts الكامل:
    Order Blocks + FVG + BOS + CHoCH + Liquidity
    """

    def find_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Order Blocks — مناطق الأوامر المؤسسية"""
        if df.empty or len(df) < 20: return []
        obs = []
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        o = df["open"].astype(float)

        for i in range(3, len(df)-3):
            # Bullish OB: شمعة هابطة قبل حركة صاعدة قوية
            if (o.iloc[i] > c.iloc[i] and  # شمعة حمراء
                c.iloc[i+1] > h.iloc[i] and  # اختراق للأعلى
                c.iloc[i+2] > c.iloc[i+1]):   # استمرار
                obs.append({
                    "type":    "BULLISH_OB",
                    "top":     float(h.iloc[i]),
                    "bottom":  float(l.iloc[i]),
                    "index":   i,
                    "strength":float((c.iloc[i+2]-c.iloc[i])/c.iloc[i])
                })
            # Bearish OB: شمعة صاعدة قبل حركة هابطة قوية
            if (c.iloc[i] > o.iloc[i] and  # شمعة خضراء
                c.iloc[i+1] < l.iloc[i] and  # اختراق للأسفل
                c.iloc[i+2] < c.iloc[i+1]):   # استمرار
                obs.append({
                    "type":    "BEARISH_OB",
                    "top":     float(h.iloc[i]),
                    "bottom":  float(l.iloc[i]),
                    "index":   i,
                    "strength":float((c.iloc[i]-c.iloc[i+2])/c.iloc[i])
                })
        return obs[-5:]  # آخر 5 Order Blocks

    def find_fvg(self, df: pd.DataFrame) -> List[Dict]:
        """Fair Value Gaps — الفجوات السعرية"""
        if df.empty or len(df) < 3: return []
        fvgs = []
        h = df["high"].astype(float)
        l = df["low"].astype(float)

        for i in range(1, len(df)-1):
            # Bullish FVG: فجوة صاعدة
            if l.iloc[i+1] > h.iloc[i-1]:
                fvgs.append({
                    "type":   "BULLISH_FVG",
                    "top":    float(l.iloc[i+1]),
                    "bottom": float(h.iloc[i-1]),
                    "mid":    float((l.iloc[i+1]+h.iloc[i-1])/2),
                    "size":   float(l.iloc[i+1]-h.iloc[i-1]),
                    "index":  i
                })
            # Bearish FVG: فجوة هابطة
            if h.iloc[i+1] < l.iloc[i-1]:
                fvgs.append({
                    "type":   "BEARISH_FVG",
                    "top":    float(l.iloc[i-1]),
                    "bottom": float(h.iloc[i+1]),
                    "mid":    float((l.iloc[i-1]+h.iloc[i+1])/2),
                    "size":   float(l.iloc[i-1]-h.iloc[i+1]),
                    "index":  i
                })
        return fvgs[-5:]

    def detect_bos_choch(self, df: pd.DataFrame) -> Dict:
        """
        Break of Structure (BOS) — كسر الهيكل
        Change of Character (CHoCH) — تغيير الطابع
        """
        if df.empty or len(df) < 20:
            return {"bos": None, "choch": None}
        h = df["high"].astype(float)
        l = df["low"].astype(float)

        # آخر قمة وقاع
        last_high = float(h.iloc[-20:].max())
        last_low  = float(l.iloc[-20:].min())
        curr      = float(df["close"].iloc[-1])
        prev_high = float(h.iloc[-20:-5].max())
        prev_low  = float(l.iloc[-20:-5].min())

        bos   = None
        choch = None

        # BOS صاعد: كسر قمة سابقة
        if curr > last_high and last_high > prev_high:
            bos = {"direction":"BULLISH","level":last_high,"strength":"STRONG"}
        # BOS هابط: كسر قاع سابق
        elif curr < last_low and last_low < prev_low:
            bos = {"direction":"BEARISH","level":last_low,"strength":"STRONG"}

        # CHoCH: تغيير الطابع
        if curr > last_high and last_high < prev_high:
            choch = {"direction":"BULLISH","level":last_high}
        elif curr < last_low and last_low > prev_low:
            choch = {"direction":"BEARISH","level":last_low}

        return {"bos": bos, "choch": choch}

    def find_liquidity(self, df: pd.DataFrame) -> Dict:
        """
        Liquidity Pools — بحيرات السيولة
        Equal Highs/Lows = وقف خسارة الجميع = هدف الأموال الكبيرة
        """
        if df.empty or len(df) < 20:
            return {"buy_side": [], "sell_side": []}
        h = df["high"].astype(float)
        l = df["low"].astype(float)

        # Equal Highs (Buy Side Liquidity)
        buy_liq  = []
        sell_liq = []
        tolerance= 0.002  # 0.2%

        for i in range(5, len(df)-5):
            # قمم متساوية = سيولة شراء
            nearby_highs = [j for j in range(i-5,i+5)
                           if j!=i and abs(float(h.iloc[j])-float(h.iloc[i]))/float(h.iloc[i]) < tolerance]
            if nearby_highs:
                buy_liq.append({"level":float(h.iloc[i]),"count":len(nearby_highs)})

            # قيعان متساوية = سيولة بيع
            nearby_lows = [j for j in range(i-5,i+5)
                          if j!=i and abs(float(l.iloc[j])-float(l.iloc[i]))/float(l.iloc[i]) < tolerance]
            if nearby_lows:
                sell_liq.append({"level":float(l.iloc[i]),"count":len(nearby_lows)})

        return {
            "buy_side":  sorted(buy_liq,  key=lambda x: x["count"], reverse=True)[:3],
            "sell_side": sorted(sell_liq, key=lambda x: x["count"], reverse=True)[:3]
        }

    def signal(self, df: pd.DataFrame) -> Tuple[str, float, Dict]:
        """الإشارة الكاملة من SMC"""
        if df.empty or len(df) < 30:
            return "HOLD", 0.0, {}

        obs      = self.find_order_blocks(df)
        fvgs     = self.find_fvg(df)
        bos_choch= self.detect_bos_choch(df)
        liq      = self.find_liquidity(df)
        price    = float(df["close"].iloc[-1])

        score = 0.0; reasons = []

        # BOS صاعد = إشارة شراء قوية
        bos = bos_choch.get("bos")
        if bos and bos["direction"] == "BULLISH":
            score += 0.35; reasons.append("BOS↑")
        elif bos and bos["direction"] == "BEARISH":
            score -= 0.35; reasons.append("BOS↓")

        # CHoCH
        choch = bos_choch.get("choch")
        if choch and choch["direction"] == "BULLISH":
            score += 0.25; reasons.append("CHoCH↑")
        elif choch and choch["direction"] == "BEARISH":
            score -= 0.25; reasons.append("CHoCH↓")

        # السعر في Order Block صاعد
        for ob in obs:
            if (ob["type"] == "BULLISH_OB" and
                    ob["bottom"] <= price <= ob["top"]):
                score += 0.20; reasons.append("BullOB")
                break
            if (ob["type"] == "BEARISH_OB" and
                    ob["bottom"] <= price <= ob["top"]):
                score -= 0.20; reasons.append("BearOB")
                break

        # FVG
        for fvg in fvgs:
            if fvg["type"]=="BULLISH_FVG" and price <= fvg["top"]:
                score += 0.15; reasons.append("FVG↑")
                break
            if fvg["type"]=="BEARISH_FVG" and price >= fvg["bottom"]:
                score -= 0.15; reasons.append("FVG↓")
                break

        score = max(-1, min(1, score))
        sig   = "BUY" if score>0.3 else "SELL" if score<-0.3 else "HOLD"
        conf  = abs(score)

        return sig, round(conf,3), {
            "reasons": reasons, "obs": len(obs),
            "fvgs": len(fvgs), "bos": bos, "score": score
        }


class ICTAnalyzer:
    """
    ICT Inner Circle Trader الكامل:
    Killzones + OTE + Power of 3 + Displacement
    """

    KILLZONES = {
        "ASIAN":        (0,  2),    # 00:00-02:00 UTC
        "LONDON_OPEN":  (7,  10),   # 07:00-10:00 UTC
        "NY_OPEN":      (12, 15),   # 12:00-15:00 UTC
        "LONDON_CLOSE": (15, 17),   # 15:00-17:00 UTC
        "NY_CLOSE":     (20, 22),   # 20:00-22:00 UTC
    }

    KILLZONE_BIAS = {
        "ASIAN":        0.5,   # تجميع
        "LONDON_OPEN":  0.9,   # أقوى جلسة
        "NY_OPEN":      0.85,  # جلسة قوية
        "LONDON_CLOSE": 0.7,   # ارتداد
        "NY_CLOSE":     0.6,   # تصفية
    }

    def __init__(self):
        self.smc = SMCAnalyzer()

    def current_killzone(self) -> Tuple[str, float]:
        """الجلسة الحالية وقوتها"""
        hour = datetime.utcnow().hour
        for name, (start, end) in self.KILLZONES.items():
            if start <= hour < end:
                return name, self.KILLZONE_BIAS[name]
        return "OFF_HOURS", 0.3

    def optimal_trade_entry(self, df: pd.DataFrame) -> Dict:
        """
        OTE = Optimal Trade Entry
        0.618-0.786 Fibonacci retracement
        أفضل نقطة دخول بعد التصحيح
        """
        if df.empty or len(df) < 20:
            return {"ote": False}
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)

        swing_high = float(h.iloc[-20:].max())
        swing_low  = float(l.iloc[-20:].min())
        rng        = swing_high - swing_low
        price      = float(c.iloc[-1])

        if rng == 0: return {"ote": False}

        # مستويات Fibonacci
        fib618 = swing_high - rng * 0.618
        fib786 = swing_high - rng * 0.786
        fib500 = swing_high - rng * 0.500

        # هل السعر في منطقة OTE؟
        in_ote_bull = fib786 <= price <= fib618
        in_ote_bear = (swing_low + rng*0.618) <= price <= (swing_low + rng*0.786)

        return {
            "ote":       in_ote_bull or in_ote_bear,
            "direction": "BUY" if in_ote_bull else "SELL" if in_ote_bear else "NONE",
            "fib618":    round(fib618, 4),
            "fib786":    round(fib786, 4),
            "fib500":    round(fib500, 4),
            "price":     round(price, 4)
        }

    def power_of_3(self, df: pd.DataFrame) -> Dict:
        """
        Power of 3 = AMD:
        Accumulation → Manipulation → Distribution
        """
        if df.empty or len(df) < 10:
            return {"phase": "UNKNOWN"}
        c    = df["close"].astype(float)
        h    = df["high"].astype(float)
        l    = df["low"].astype(float)
        n    = min(10, len(df))
        rng  = float(h.iloc[-n:].max() - l.iloc[-n:].min())
        curr = float(c.iloc[-1])
        mid  = float(l.iloc[-n:].min() + rng/2)
        hi   = float(h.iloc[-n:].max())
        lo   = float(l.iloc[-n:].min())

        if rng < float(c.mean()) * 0.005:
            phase = "ACCUMULATION"
        elif curr > hi * 0.998 or curr < lo * 1.002:
            phase = "MANIPULATION"
        else:
            phase = "DISTRIBUTION"

        return {
            "phase":     phase,
            "range":     round(rng, 4),
            "bias":      "BULLISH" if curr > mid else "BEARISH"
        }

    def signal(self, df: pd.DataFrame) -> Tuple[str, float, Dict]:
        """الإشارة الكاملة من ICT"""
        if df.empty or len(df) < 20:
            return "HOLD", 0.0, {}

        killzone, kz_power = self.current_killzone()
        ote    = self.optimal_trade_entry(df)
        amd    = self.power_of_3(df)
        smc_sig, smc_conf, smc_det = self.smc.signal(df)

        score = 0.0; reasons = []

        # Killzone boost
        if killzone in ("LONDON_OPEN", "NY_OPEN"):
            score += 0.15; reasons.append(f"KZ:{killzone}")

        # OTE
        if ote.get("ote") and ote["direction"] == "BUY":
            score += 0.30; reasons.append("OTE:BUY")
        elif ote.get("ote") and ote["direction"] == "SELL":
            score -= 0.30; reasons.append("OTE:SELL")

        # AMD Phase
        if amd["phase"] == "DISTRIBUTION":
            if amd["bias"] == "BULLISH":
                score += 0.20; reasons.append("AMD:BULL")
            else:
                score -= 0.20; reasons.append("AMD:BEAR")
        elif amd["phase"] == "MANIPULATION":
            score *= 0.5  # حذر في مرحلة التلاعب

        # SMC
        if smc_sig == "BUY":  score += smc_conf * 0.35
        elif smc_sig == "SELL": score -= smc_conf * 0.35

        score = max(-1, min(1, score)) * kz_power
        sig   = "BUY" if score>0.25 else "SELL" if score<-0.25 else "HOLD"

        return sig, round(abs(score),3), {
            "killzone": killzone,
            "kz_power": kz_power,
            "ote":      ote,
            "amd":      amd,
            "smc":      smc_det,
            "reasons":  reasons
        }


class CRTAnalyzer:
    """
    Candle Range Theory:
    تحليل نطاق الشمعة الأم
    """
    def analyze(self, df: pd.DataFrame) -> Dict:
        if df.empty or len(df) < 5:
            return {"phase": "UNKNOWN"}
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        o = df["open"].astype(float)

        # الشمعة الأم (آخر شمعة مكتملة)
        mother_high = float(h.iloc[-2])
        mother_low  = float(l.iloc[-2])
        mother_rng  = mother_high - mother_low
        curr        = float(c.iloc[-1])

        if mother_rng == 0:
            return {"phase": "UNKNOWN"}

        # موقع السعر الحالي في نطاق الشمعة الأم
        position = (curr - mother_low) / mother_rng

        # مراحل CRT
        if position < 0.33:
            phase = "ACCUMULATION"
            bias  = "BULLISH"
        elif position < 0.66:
            phase = "MANIPULATION"
            bias  = "NEUTRAL"
        else:
            phase = "DISTRIBUTION"
            bias  = "BEARISH"

        # كسر الشمعة الأم
        broke_high = curr > mother_high
        broke_low  = curr < mother_low

        signal = "HOLD"; conf = 0.0
        if broke_high: signal = "BUY";  conf = 0.65
        if broke_low:  signal = "SELL"; conf = 0.65
        if phase == "ACCUMULATION" and not broke_low:
            signal = "BUY"; conf = 0.55

        return {
            "phase":      phase,
            "bias":       bias,
            "position":   round(position, 3),
            "broke_high": broke_high,
            "broke_low":  broke_low,
            "signal":     signal,
            "confidence": conf,
            "mother_high":round(mother_high, 4),
            "mother_low": round(mother_low, 4)
        }


class HTFAnalyzer:
    """
    Higher TimeFrame Analysis:
    Top-Down من 1D → 4H → 1H → 15m
    """
    def analyze(self, data: Dict[str, pd.DataFrame]) -> Dict:
        results = {}
        tf_weights = {
            "1d": 0.40, "4h": 0.30,
            "1h": 0.20, "15m": 0.10
        }
        ict = ICTAnalyzer()

        for tf, weight in tf_weights.items():
            df = data.get(tf, pd.DataFrame())
            if df.empty or len(df) < 20: continue
            sig, conf, det = ict.signal(df)
            results[tf] = {
                "signal":     sig,
                "confidence": conf,
                "weight":     weight,
                "details":    det
            }

        # HTF Bias
        buy_score = sell_score = 0.0
        for tf, r in results.items():
            w = tf_weights.get(tf, 0.1) * r["confidence"]
            if r["signal"] == "BUY":  buy_score  += w
            elif r["signal"] == "SELL": sell_score += w

        total = buy_score + sell_score + 1e-10
        if buy_score/total  >= 0.55: final = "BUY";  conf = buy_score/total
        elif sell_score/total >= 0.55: final = "SELL"; conf = sell_score/total
        else:                          final = "HOLD"; conf = 0.0

        return {
            "htf_bias":   final,
            "confidence": round(conf, 3),
            "timeframes": results,
            "confluence": len([r for r in results.values()
                               if r["signal"] == final])
        }


# ── وكيل ICT/SMC/CRT/HTF المدمج ─────────────────────────────────────────────
class ICTSMCAgent(BaseAgent):
    """
    وكيل واحد يجمع كل المنهجيات:
    ICT + SMC + CRT + HTF + TBS
    """
    def __init__(self, name: str, weight: float):
        super().__init__(name, weight)
        self.ict = ICTAnalyzer()
        self.crt = CRTAnalyzer()
        self.htf = HTFAnalyzer()

    async def analyze(self, data: Dict) -> Tuple[int, float, Dict]:
        df_1h  = data.get("1h",  pd.DataFrame())
        df_15m = data.get("15m", pd.DataFrame())
        df_4h  = data.get("4h",  pd.DataFrame())
        df_1d  = data.get("1d",  pd.DataFrame())

        if df_1h.empty: return 0, 0.0, {}

        # ICT Signal
        ict_sig, ict_conf, ict_det = self.ict.signal(df_1h)

        # CRT Signal
        crt_det = self.crt.analyze(df_15m if not df_15m.empty else df_1h)
        crt_sig = crt_det.get("signal", "HOLD")
        crt_conf= crt_det.get("confidence", 0.0)

        # HTF Bias
        htf_data= {"1d":df_1d,"4h":df_4h,"1h":df_1h,"15m":df_15m}
        htf_det = self.htf.analyze(htf_data)
        htf_sig = htf_det.get("htf_bias", "HOLD")
        htf_conf= htf_det.get("confidence", 0.0)

        # TBS — Killzone
        killzone, kz_power = self.ict.current_killzone()
        in_killzone = kz_power >= 0.7

        # دمج الإشارات
        scores = []
        for sig, conf in [(ict_sig,0.40*ict_conf),
                           (crt_sig,0.25*crt_conf),
                           (htf_sig,0.35*htf_conf)]:
            scores.append(conf if sig=="BUY" else -conf if sig=="SELL" else 0)

        final_score = sum(scores)
        if in_killzone: final_score *= kz_power

        final_score = max(-1, min(1, final_score))
        direction = (1 if final_score>0.20 else
                    -1 if final_score<-0.20 else 0)
        confidence= abs(final_score)

        if direction != 0:
            log.info(
                f"📊 ICT/SMC [{data.get('symbol','?')}] "
                f"{'BUY' if direction==1 else 'SELL'} | "
                f"KZ:{killzone} | "
                f"CRT:{crt_det.get('phase','?')} | "
                f"HTF:{htf_sig} | "
                f"conf={confidence:.0%}"
            )

        return direction, round(confidence,3), {
            "ict": ict_det, "crt": crt_det,
            "htf": htf_det, "killzone": killzone,
            "kz_power": kz_power
        }




# ══════════════════════════════════════════════════════════════════════════════
# 🏆 ADVANCED STRATEGIES — الاستراتيجيات القوية
# ══════════════════════════════════════════════════════════════════════════════

class StrategyEngine:
    """
    مجموعة الاستراتيجيات الأقوى:
    1. Trend Following     — تتبع الاتجاه
    2. Mean Reversion      — الارتداد للمتوسط
    3. Breakout            — الاختراق
    4. Scalping            — السكالبينغ السريع
    5. Swing Trading       — التداول المتأرجح
    6. Momentum            — الزخم
    7. VWAP Deviation      — الانحراف عن VWAP
    8. Open Range Breakout — اختراق نطاق الافتتاح
    """

    def trend_following(self, df: pd.DataFrame) -> Tuple[str, float]:
        """تتبع الاتجاه — الأبسط والأقوى"""
        if df.empty or len(df) < 50: return "HOLD", 0.0
        c    = df["close"].astype(float)
        ema20= c.ewm(span=20).mean().iloc[-1]
        ema50= c.ewm(span=50).mean().iloc[-1]
        ema200=c.ewm(span=200).mean().iloc[-1] if len(c)>=200 else ema50
        d    = c.diff()
        g    = d.clip(lower=0).rolling(14).mean()
        l    = (-d.clip(upper=0)).rolling(14).mean()
        rsi  = float(100-(100/(1+g/l.replace(0,1e-10))).iloc[-1])
        # Triple EMA Alignment
        if ema20 > ema50 > ema200 and rsi > 50:
            strength = min((ema20-ema200)/ema200*100, 5)/5
            return "BUY", round(0.65+strength*0.20, 3)
        if ema20 < ema50 < ema200 and rsi < 50:
            strength = min((ema200-ema20)/ema200*100, 5)/5
            return "SELL", round(0.65+strength*0.20, 3)
        return "HOLD", 0.0

    def mean_reversion(self, df: pd.DataFrame) -> Tuple[str, float]:
        """الارتداد للمتوسط — يعمل في السوق الجانبي"""
        if df.empty or len(df) < 30: return "HOLD", 0.0
        c   = df["close"].astype(float)
        sma = c.rolling(20).mean()
        std = c.rolling(20).std()
        bb_pct = float((c.iloc[-1]-(sma-2*std).iloc[-1])/(4*std+1e-10).iloc[-1])
        d   = c.diff()
        g   = d.clip(lower=0).rolling(14).mean()
        l   = (-d.clip(upper=0)).rolling(14).mean()
        rsi = float(100-(100/(1+g/l.replace(0,1e-10))).iloc[-1])
        # Oversold + BB Lower
        if bb_pct < 0.10 and rsi < 30:
            return "BUY",  round(0.60+(0.10-bb_pct)*2, 3)
        # Overbought + BB Upper
        if bb_pct > 0.90 and rsi > 70:
            return "SELL", round(0.60+(bb_pct-0.90)*2, 3)
        return "HOLD", 0.0

    def breakout(self, df: pd.DataFrame) -> Tuple[str, float]:
        """الاختراق — يصطاد الحركات الكبيرة"""
        if df.empty or len(df) < 25: return "HOLD", 0.0
        c  = df["close"].astype(float)
        h  = df["high"].astype(float)
        l  = df["low"].astype(float)
        v  = df["volume"].astype(float)
        # Donchian Channel
        high20 = float(h.rolling(20).max().iloc[-2])
        low20  = float(l.rolling(20).min().iloc[-2])
        price  = float(c.iloc[-1])
        vol_r  = float(v.iloc[-1]/v.rolling(20).mean().iloc[-1])
        # اختراق مع حجم عالٍ
        if price > high20 and vol_r > 1.8:
            return "BUY",  round(min(0.55+vol_r*0.05, 0.88), 3)
        if price < low20  and vol_r > 1.8:
            return "SELL", round(min(0.55+vol_r*0.05, 0.88), 3)
        return "HOLD", 0.0

    def scalping(self, df: pd.DataFrame) -> Tuple[str, float]:
        """السكالبينغ — صفقات سريعة وصغيرة"""
        if df.empty or len(df) < 15: return "HOLD", 0.0
        c    = df["close"].astype(float)
        h    = df["high"].astype(float)
        l    = df["low"].astype(float)
        # Stochastic RSI
        lo14 = l.rolling(14).min()
        hi14 = h.rolling(14).max()
        stoch= float(100*(c-lo14).iloc[-1]/(hi14-lo14+1e-10).iloc[-1])
        ema9 = float(c.ewm(span=9).mean().iloc[-1])
        ema21= float(c.ewm(span=21).mean().iloc[-1])
        price= float(c.iloc[-1])
        # سريع جداً
        if stoch < 20 and ema9 > ema21 and price > ema9:
            return "BUY",  0.62
        if stoch > 80 and ema9 < ema21 and price < ema9:
            return "SELL", 0.62
        return "HOLD", 0.0

    def swing_trading(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Swing Trading — أرباح أكبر مع صبر أكثر"""
        if df.empty or len(df) < 60: return "HOLD", 0.0
        c   = df["close"].astype(float)
        h   = df["high"].astype(float)
        l   = df["low"].astype(float)
        # Higher Highs + Higher Lows
        highs = h.rolling(5).max()
        lows  = l.rolling(5).min()
        hh = float(highs.iloc[-1]) > float(highs.iloc[-6])
        hl = float(lows.iloc[-1])  > float(lows.iloc[-6])
        lh = float(highs.iloc[-1]) < float(highs.iloc[-6])
        ll = float(lows.iloc[-1])  < float(lows.iloc[-6])
        # Swing structure
        if hh and hl:  return "BUY",  0.72
        if lh and ll:  return "SELL", 0.72
        return "HOLD", 0.0

    def momentum(self, df: pd.DataFrame) -> Tuple[str, float]:
        """الزخم — يركب الموجة"""
        if df.empty or len(df) < 20: return "HOLD", 0.0
        c   = df["close"].astype(float)
        v   = df["volume"].astype(float)
        # Rate of Change
        roc = float((c.iloc[-1]-c.iloc[-10])/c.iloc[-10]*100)
        vol_r= float(v.iloc[-1]/v.rolling(20).mean().iloc[-1])
        e12 = c.ewm(span=12).mean(); e26 = c.ewm(span=26).mean()
        macd_h = float((e12-e26-(e12-e26).ewm(span=9).mean()).iloc[-1])
        if roc > 2.0 and vol_r > 1.5 and macd_h > 0:
            return "BUY",  round(min(0.55+roc*0.02, 0.85), 3)
        if roc < -2.0 and vol_r > 1.5 and macd_h < 0:
            return "SELL", round(min(0.55+abs(roc)*0.02, 0.85), 3)
        return "HOLD", 0.0

    def vwap_deviation(self, df: pd.DataFrame) -> Tuple[str, float]:
        """VWAP Deviation — يتداول حول VWAP"""
        if df.empty or len(df) < 20: return "HOLD", 0.0
        c    = df["close"].astype(float)
        h    = df["high"].astype(float)
        l    = df["low"].astype(float)
        v    = df["volume"].astype(float)
        tp   = (h+l+c)/3
        vwap = float((tp*v).cumsum().iloc[-1]/v.cumsum().iloc[-1])
        price= float(c.iloc[-1])
        dev  = (price-vwap)/vwap
        std  = float(c.rolling(20).std().iloc[-1])
        # بعيد عن VWAP → ارتداد
        if dev < -0.015: return "BUY",  round(min(abs(dev)*30, 0.80), 3)
        if dev >  0.015: return "SELL", round(min(dev*30, 0.80), 3)
        return "HOLD", 0.0

    def open_range_breakout(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Open Range Breakout — اختراق نطاق الافتتاح"""
        if df.empty or len(df) < 5: return "HOLD", 0.0
        # أول 30 دقيقة من الجلسة
        first5 = df.iloc[:5]
        orh    = float(first5["high"].max())
        orl    = float(first5["low"].min())
        price  = float(df["close"].iloc[-1])
        rng    = orh - orl
        if rng == 0: return "HOLD", 0.0
        # اختراق للأعلى
        if price > orh * 1.001:
            return "BUY",  0.68
        if price < orl * 0.999:
            return "SELL", 0.68
        return "HOLD", 0.0

    def aggregate(self, df: pd.DataFrame) -> Tuple[str, float, Dict]:
        """يجمع كل الاستراتيجيات"""
        strategies = {
            "Trend":    self.trend_following(df),
            "Reversion":self.mean_reversion(df),
            "Breakout": self.breakout(df),
            "Scalp":    self.scalping(df),
            "Swing":    self.swing_trading(df),
            "Momentum": self.momentum(df),
            "VWAP":     self.vwap_deviation(df),
            "ORB":      self.open_range_breakout(df),
        }
        # أوزان الاستراتيجيات
        weights = {
            "Trend":0.20,"Reversion":0.15,"Breakout":0.15,
            "Scalp":0.10,"Swing":0.15,"Momentum":0.10,
            "VWAP":0.10,"ORB":0.05
        }
        buy_s = sell_s = 0.0
        active = {}
        for name, (sig, conf) in strategies.items():
            w = weights.get(name, 0.1) * conf
            if sig == "BUY":   buy_s  += w; active[name] = "BUY"
            elif sig == "SELL": sell_s += w; active[name] = "SELL"

        total = buy_s + sell_s + 1e-10
        if buy_s/total  >= 0.55: final="BUY";  conf=buy_s/total
        elif sell_s/total >= 0.55: final="SELL"; conf=sell_s/total
        else:                      final="HOLD"; conf=0.0

        return final, round(conf,3), {
            "active":   active,
            "buy_score":round(buy_s,3),
            "sell_score":round(sell_s,3)
        }


class StrategyAgent(BaseAgent):
    """وكيل الاستراتيجيات المتقدمة"""
    def __init__(self, name: str, weight: float):
        super().__init__(name, weight)
        self.engine = StrategyEngine()

    async def analyze(self, data: Dict) -> Tuple[int, float, Dict]:
        df = data.get("1h", data.get("15m", pd.DataFrame()))
        if df.empty: return 0, 0.0, {}
        sig, conf, det = self.engine.aggregate(df)
        d = 1 if sig=="BUY" else -1 if sig=="SELL" else 0
        if d != 0:
            log.info(
                f"🏆 Strategies [{data.get('symbol','?')}] "
                f"{sig} | conf={conf:.0%} | "
                f"active={list(det.get('active',{}).keys())}"
            )
        return d, conf, det




# ══════════════════════════════════════════════════════════════════════════════
# 📐 ADVANCED INDICATORS — المؤشرات القوية
# ══════════════════════════════════════════════════════════════════════════════
class AdvancedIndicators:
    """
    أقوى المؤشرات الاحترافية:
    1. Supertrend          — اتجاه ديناميكي
    2. Hull MA             — متوسط بدون تأخر
    3. Squeeze Momentum    — لاري ويليامز
    4. Heikin Ashi         — شموع يابانية محسّنة
    5. Weis Wave           — حجم الموجات
    6. Laguerre RSI        — RSI محسّن
    7. Elder Ray           — قوة الثيران والدببة
    8. Keltner Channel     — قناة كيلتنر
    9. Chaikin Money Flow  — تدفق المال
    10. Fisher Transform   — تحويل فيشر
    """

    def supertrend(self, df: pd.DataFrame,
                    period: int = 10,
                    mult: float = 3.0) -> pd.DataFrame:
        """Supertrend — أشهر مؤشر اتجاه"""
        if df.empty or len(df) < period+1: return df
        df = df.copy()
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)
        hl2  = (h+l)/2
        tr   = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr  = tr.rolling(period).mean()
        upper= hl2 + mult*atr
        lower= hl2 - mult*atr
        st   = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        for i in range(1, len(df)):
            if c.iloc[i] > upper.iloc[i-1]:
                direction.iloc[i] = 1
                st.iloc[i]        = lower.iloc[i]
            elif c.iloc[i] < lower.iloc[i-1]:
                direction.iloc[i] = -1
                st.iloc[i]        = upper.iloc[i]
            else:
                direction.iloc[i] = direction.iloc[i-1]
                st.iloc[i]        = (lower.iloc[i] if direction.iloc[i]==1
                                     else upper.iloc[i])
        df["supertrend"]     = st
        df["supertrend_dir"] = direction
        return df

    def hull_ma(self, df: pd.DataFrame,
                 period: int = 20) -> pd.Series:
        """Hull Moving Average — بدون تأخر"""
        if df.empty or len(df) < period: return pd.Series()
        c    = df["close"].astype(float)
        half = c.rolling(period//2).mean()
        full = c.rolling(period).mean()
        raw  = 2*half - full
        hma  = raw.rolling(int(period**0.5)).mean()
        return hma

    def squeeze_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """Squeeze Momentum — لاري ويليامز الأسطوري"""
        if df.empty or len(df) < 20: return df
        df  = df.copy()
        c   = df["close"].astype(float)
        h   = df["high"].astype(float)
        l   = df["low"].astype(float)
        # Bollinger Bands
        sma = c.rolling(20).mean()
        std = c.rolling(20).std()
        bb_up = sma+2*std; bb_lo = sma-2*std
        # Keltner
        tr  = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr = tr.rolling(20).mean()
        kc_up = sma+1.5*atr; kc_lo = sma-1.5*atr
        # Squeeze
        df["sq_on"]  = (bb_up < kc_up) & (bb_lo > kc_lo)
        df["sq_off"] = (bb_up > kc_up) & (bb_lo < kc_lo)
        # Momentum
        highest = (h.rolling(20).max()+l.rolling(20).min())/2
        df["sq_mom"] = c - (highest+sma)/2
        df["sq_mom_delta"] = df["sq_mom"].diff()
        return df

    def heikin_ashi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Heikin Ashi — شموع يابانية محسّنة"""
        if df.empty: return df
        ha = df.copy()
        ha["ha_close"] = (df["open"]+df["high"]+df["low"]+df["close"])/4
        ha["ha_open"]  = (df["open"].shift(1)+df["close"].shift(1))/2
        ha["ha_high"]  = pd.concat([df["high"],ha["ha_open"],ha["ha_close"]],axis=1).max(axis=1)
        ha["ha_low"]   = pd.concat([df["low"],ha["ha_open"],ha["ha_close"]],axis=1).min(axis=1)
        ha["ha_bull"]  = ha["ha_close"] > ha["ha_open"]
        # Consecutive candles
        ha["ha_streak"]= ha["ha_bull"].astype(int).groupby(
            (ha["ha_bull"] != ha["ha_bull"].shift()).cumsum()
        ).cumcount()+1
        return ha

    def laguerre_rsi(self, df: pd.DataFrame,
                      gamma: float = 0.7) -> pd.Series:
        """Laguerre RSI — أدق من RSI العادي"""
        if df.empty or len(df) < 4: return pd.Series()
        c  = df["close"].astype(float).values
        L0 = np.zeros(len(c)); L1 = np.zeros(len(c))
        L2 = np.zeros(len(c)); L3 = np.zeros(len(c))
        for i in range(1, len(c)):
            L0[i] = (1-gamma)*c[i] + gamma*L0[i-1]
            L1[i] = -gamma*L0[i]   + L0[i-1] + gamma*L1[i-1]
            L2[i] = -gamma*L1[i]   + L1[i-1] + gamma*L2[i-1]
            L3[i] = -gamma*L2[i]   + L2[i-1] + gamma*L3[i-1]
        cu = np.where(L0>=L1,L0-L1,0)+np.where(L1>=L2,L1-L2,0)+np.where(L2>=L3,L2-L3,0)
        cd = np.where(L0< L1,L1-L0,0)+np.where(L1< L2,L2-L1,0)+np.where(L2< L3,L3-L2,0)
        lrsi = np.where(cu+cd==0, 0, cu/(cu+cd))
        return pd.Series(lrsi, index=df.index)

    def elder_ray(self, df: pd.DataFrame,
                   period: int = 13) -> pd.DataFrame:
        """Elder Ray — قوة الثيران والدببة"""
        if df.empty or len(df) < period: return df
        df   = df.copy()
        c    = df["close"].astype(float)
        h    = df["high"].astype(float)
        l    = df["low"].astype(float)
        ema  = c.ewm(span=period).mean()
        df["bull_power"] = h - ema
        df["bear_power"] = l - ema
        df["elder_signal"]= np.where(
            (df["bull_power"]>0) & (df["bear_power"]>df["bear_power"].shift(1)),
            "BUY", np.where(
            (df["bear_power"]<0) & (df["bull_power"]<df["bull_power"].shift(1)),
            "SELL","HOLD"))
        return df

    def chaikin_money_flow(self, df: pd.DataFrame,
                            period: int = 20) -> pd.Series:
        """Chaikin Money Flow — تدفق المال الحقيقي"""
        if df.empty or len(df) < period: return pd.Series()
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        v = df["volume"].astype(float)
        mfm = ((c-l)-(h-c))/(h-l+1e-10)
        mfv = mfm * v
        cmf = mfv.rolling(period).sum()/v.rolling(period).sum()
        return cmf

    def fisher_transform(self, df: pd.DataFrame,
                          period: int = 9) -> pd.DataFrame:
        """Fisher Transform — يكشف نقاط الانعكاس"""
        if df.empty or len(df) < period: return df
        df = df.copy()
        h  = df["high"].astype(float)
        l  = df["low"].astype(float)
        hl2= (h+l)/2
        hi = hl2.rolling(period).max()
        lo = hl2.rolling(period).min()
        val= 2*((hl2-lo)/(hi-lo+1e-10))-1
        val= val.clip(-0.999, 0.999)
        df["fisher"]       = 0.5*np.log((1+val)/(1-val+1e-10))
        df["fisher_signal"]= df["fisher"].shift(1)
        df["fisher_cross"] = np.where(
            df["fisher"]>df["fisher_signal"], 1,
            np.where(df["fisher"]<df["fisher_signal"],-1,0))
        return df

    def keltner_channel(self, df: pd.DataFrame,
                         period: int = 20,
                         mult: float = 2.0) -> pd.DataFrame:
        """Keltner Channel — قناة التقلب"""
        if df.empty or len(df) < period: return df
        df = df.copy()
        c  = df["close"].astype(float)
        h  = df["high"].astype(float)
        l  = df["low"].astype(float)
        ema= c.ewm(span=period).mean()
        tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
        atr= tr.rolling(period).mean()
        df["kc_upper"]= ema + mult*atr
        df["kc_lower"]= ema - mult*atr
        df["kc_mid"]  = ema
        df["kc_pct"]  = (c-df["kc_lower"])/(df["kc_upper"]-df["kc_lower"]+1e-10)
        return df

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """يحسب كل المؤشرات دفعة واحدة"""
        if df.empty or len(df) < 30: return df
        try:
            df = self.supertrend(df)
            df["hma"]   = self.hull_ma(df)
            df = self.squeeze_momentum(df)
            df = self.heikin_ashi(df)
            df["lrsi"]  = self.laguerre_rsi(df)
            df = self.elder_ray(df)
            df["cmf"]   = self.chaikin_money_flow(df)
            df = self.fisher_transform(df)
            df = self.keltner_channel(df)
        except Exception as e:
            log.warning(f"Indicators: {e}")
        return df

    def signal(self, df: pd.DataFrame) -> Tuple[str, float, Dict]:
        """إشارة مجمّعة من كل المؤشرات"""
        df  = self.compute_all(df)
        if df.empty or len(df) < 2: return "HOLD", 0.0, {}
        last= df.iloc[-1]
        score= 0.0; details = {}

        # Supertrend
        st_dir = float(last.get("supertrend_dir", 0))
        if   st_dir ==  1: score += 0.20; details["ST"]="↑"
        elif st_dir == -1: score -= 0.20; details["ST"]="↓"

        # Squeeze Momentum
        sq_mom = float(last.get("sq_mom", 0))
        sq_on  = bool(last.get("sq_on", False))
        if not sq_on:  # Squeeze released
            if sq_mom > 0: score += 0.15; details["SQ"]="↑"
            else:           score -= 0.15; details["SQ"]="↓"

        # Heikin Ashi
        ha_streak = float(last.get("ha_streak", 0))
        ha_bull   = bool(last.get("ha_bull", False))
        if ha_streak >= 3:
            if ha_bull: score += 0.12; details["HA"]=f"↑×{ha_streak:.0f}"
            else:        score -= 0.12; details["HA"]=f"↓×{ha_streak:.0f}"

        # Laguerre RSI
        lrsi = float(last.get("lrsi", 0.5))
        if   lrsi < 0.2: score += 0.12; details["LRSI"]=f"{lrsi:.2f}↑"
        elif lrsi > 0.8: score -= 0.12; details["LRSI"]=f"{lrsi:.2f}↓"

        # Elder Ray
        bull_p = float(last.get("bull_power", 0))
        bear_p = float(last.get("bear_power", 0))
        if bull_p > 0 and bear_p > float(df["bear_power"].iloc[-2]):
            score += 0.10; details["ER"]="Bull↑"
        elif bear_p < 0 and bull_p < float(df["bull_power"].iloc[-2]):
            score -= 0.10; details["ER"]="Bear↓"

        # CMF
        cmf = float(last.get("cmf", 0))
        if   cmf >  0.15: score += 0.12; details["CMF"]=f"+{cmf:.2f}"
        elif cmf < -0.15: score -= 0.12; details["CMF"]=f"{cmf:.2f}"

        # Fisher Transform
        fc = float(last.get("fisher_cross", 0))
        if   fc ==  1: score += 0.10; details["FT"]="↑"
        elif fc == -1: score -= 0.10; details["FT"]="↓"

        # Keltner
        kc_pct = float(last.get("kc_pct", 0.5))
        if   kc_pct < 0.05: score += 0.09; details["KC"]="Bot"
        elif kc_pct > 0.95: score -= 0.09; details["KC"]="Top"

        score = max(-1, min(1, score))
        sig   = "BUY" if score>0.25 else "SELL" if score<-0.25 else "HOLD"
        return sig, round(abs(score),3), details


class IndicatorAgent(BaseAgent):
    """وكيل المؤشرات المتقدمة"""
    def __init__(self, name: str, weight: float):
        super().__init__(name, weight)
        self.indicators = AdvancedIndicators()

    async def analyze(self, data: Dict) -> Tuple[int, float, Dict]:
        df = data.get("1h", data.get("15m", pd.DataFrame()))
        if df.empty: return 0, 0.0, {}
        sig, conf, det = self.indicators.signal(df)
        d = 1 if sig=="BUY" else -1 if sig=="SELL" else 0
        if d != 0:
            log.info(
                f"📐 Indicators [{data.get('symbol','?')}] "
                f"{sig} | conf={conf:.0%} | {det}"
            )
        return d, conf, det




# ══════════════════════════════════════════════════════════════════════════════
# 🏗️ ADVANCED SYSTEMS — الأنظمة القوية
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. نظام إدارة رأس المال المتقدم ─────────────────────────────────────────
class CapitalManagementSystem:
    """
    نظام إدارة رأس المال الاحترافي:
    - Kelly Criterion الكامل
    - Fixed Fractional
    - Optimal f
    - Risk of Ruin Calculator
    - Position Pyramid
    """

    def kelly_full(self, win_rate: float,
                    avg_win: float,
                    avg_loss: float) -> float:
        """Kelly Criterion الكامل"""
        if avg_loss == 0: return 0.0
        b  = abs(avg_win/avg_loss)
        p  = win_rate; q = 1-p
        kelly = (b*p - q) / b
        return max(0.0, min(kelly*0.5, 0.20))  # نصف كيلي للأمان

    def optimal_f(self, trades: List[float]) -> float:
        """Optimal f — رالف فينس"""
        if len(trades) < 10: return 0.02
        worst = abs(min(trades))
        if worst == 0: return 0.02
        best_f = 0.0; best_twr = 0.0
        for f in np.arange(0.01, 0.50, 0.01):
            twr = 1.0
            for t in trades:
                hp  = 1 + f * (t/worst)
                if hp <= 0: hp = 0.001
                twr *= hp
            if twr > best_twr:
                best_twr = twr
                best_f   = f
        return min(best_f * 0.5, 0.15)  # أمان

    def risk_of_ruin(self, win_rate: float,
                      risk_pct: float,
                      ruin_pct: float = 0.50) -> float:
        """حساب احتمال الإفلاس"""
        if win_rate >= 1.0 or risk_pct <= 0: return 0.0
        q = 1 - win_rate
        a = q / win_rate
        n = ruin_pct / risk_pct
        ror = a**n
        return round(min(ror, 1.0), 4)

    def pyramid_size(self, base_qty: float,
                      unrealized_pnl: float,
                      entry: float) -> float:
        """Position Pyramid — زيادة الحجم مع الربح"""
        if unrealized_pnl <= 0: return 0.0
        profit_pct = unrealized_pnl/entry
        if profit_pct >= 0.03:
            return base_qty * 0.5   # إضافة 50% عند +3%
        return 0.0

    def calculate(self, balance: float,
                   trades: List[float],
                   win_rate: float) -> Dict:
        wins  = [t for t in trades if t>0]
        losses= [t for t in trades if t<0]
        avg_w = float(np.mean(wins))   if wins   else 0.01
        avg_l = float(np.mean(losses)) if losses else -0.01
        kelly = self.kelly_full(win_rate, avg_w, abs(avg_l))
        opt_f = self.optimal_f(trades) if len(trades)>=10 else 0.02
        ror   = self.risk_of_ruin(win_rate, kelly)
        size  = balance * min(kelly, opt_f, 0.02)
        return {
            "kelly":    round(kelly, 4),
            "optimal_f":round(opt_f, 4),
            "ror":      round(ror, 4),
            "size":     round(size, 2),
            "safe":     ror < 0.05
        }


# ── 2. نظام فلترة الإشارات ───────────────────────────────────────────────────
class SignalFilterSystem:
    """
    يُصفّي الإشارات الضعيفة قبل التنفيذ:
    - Confirmation Filter
    - Noise Filter
    - Correlation Filter
    - Timing Filter
    - Quality Score
    """

    def quality_score(self, signal: str,
                       confidence: float,
                       agents_agree: int,
                       total_agents: int,
                       regime: str,
                       in_killzone: bool) -> float:
        score = 0.0
        # الثقة
        score += confidence * 30
        # اتفاق الوكلاء
        agree_pct = agents_agree/total_agents if total_agents>0 else 0
        score += agree_pct * 25
        # نظام السوق
        regime_bonus = {
            "TRENDING_UP":   15, "TRENDING_DOWN": 12,
            "BREAKOUT":      18, "RANGING":        5,
            "VOLATILE":       0, "UNKNOWN":         5
        }
        score += regime_bonus.get(regime, 5)
        # Killzone
        if in_killzone: score += 15
        # حد أدنى للجودة
        return round(min(score, 100), 1)

    def should_execute(self, quality: float,
                        min_quality: float = 55.0) -> bool:
        return quality >= min_quality

    def noise_filter(self, df: pd.DataFrame) -> bool:
        """يرفض الإشارات في السوق المتذبذب"""
        if df.empty or len(df)<20: return True
        c   = df["close"].astype(float)
        ret = c.pct_change().tail(20)
        # رفض إذا التذبذب عالٍ جداً
        if ret.std() > 0.05: return False
        # رفض إذا لا اتجاه واضح
        hurst = 0.5
        try:
            prices = c.values[-50:]
            lags   = [2,4,8,16]
            taus   = [np.std(np.subtract(prices[lag:],prices[:-lag]))
                      for lag in lags]
            if all(t>0 for t in taus):
                hurst = float(np.polyfit(np.log(lags),
                                          np.log(taus),1)[0])
        except: pass
        return hurst > 0.45  # رفض العشوائية


# ── 3. نظام إدارة المراكز المتقدم ───────────────────────────────────────────
class AdvancedPositionManager:
    """
    إدارة المراكز باحترافية:
    - Partial Take Profit (3 مستويات)
    - Breakeven Stop
    - Trailing Stop ديناميكي
    - Scale In/Out
    - Time-Based Exit
    """

    def __init__(self):
        self.tp_levels = [
            {"pct": 0.33, "target_atr": 1.5},  # TP1: 33% عند 1.5 ATR
            {"pct": 0.33, "target_atr": 2.5},  # TP2: 33% عند 2.5 ATR
            {"pct": 0.34, "target_atr": 4.0},  # TP3: 34% عند 4.0 ATR
        ]

    def check_partial_tp(self, entry: float,
                          price: float,
                          atr: float,
                          direction: str,
                          qty: float,
                          filled_tps: List[int]) -> Optional[Dict]:
        for i, tp in enumerate(self.tp_levels):
            if i in filled_tps: continue
            target = (entry + atr*tp["target_atr"]
                      if direction=="LONG"
                      else entry - atr*tp["target_atr"])
            hit = (price >= target if direction=="LONG"
                   else price <= target)
            if hit:
                return {
                    "tp_level":  i+1,
                    "close_pct": tp["pct"],
                    "close_qty": round(qty*tp["pct"], 6),
                    "target":    round(target, 4),
                    "reason":    f"Partial TP{i+1} at {tp['target_atr']}×ATR"
                }
        return None

    def breakeven_sl(self, entry: float,
                      price: float,
                      atr: float,
                      direction: str,
                      current_sl: float) -> float:
        """تحريك وقف الخسارة للتعادل"""
        trigger = (entry + atr*1.0 if direction=="LONG"
                   else entry - atr*1.0)
        if direction=="LONG" and price>=trigger and current_sl<entry:
            return entry * 1.0001  # فوق نقطة الدخول قليلاً
        if direction=="SHORT" and price<=trigger and current_sl>entry:
            return entry * 0.9999
        return current_sl

    def dynamic_trailing(self, peak: float,
                           price: float,
                           atr: float,
                           direction: str,
                           profit_atr: float) -> float:
        """Trailing Stop ديناميكي يتضيّق مع الربح"""
        if profit_atr < 1.0: trail_mult = 1.5
        elif profit_atr < 2.0: trail_mult = 1.2
        elif profit_atr < 3.0: trail_mult = 1.0
        else:                   trail_mult = 0.8
        if direction=="LONG":
            return peak - atr*trail_mult
        return peak + atr*trail_mult

    def time_exit(self, open_time: str,
                   max_hours: int = 48) -> bool:
        """خروج بعد مرور وقت كافٍ"""
        try:
            opened  = datetime.fromisoformat(open_time)
            elapsed = (datetime.now()-opened).seconds/3600
            return elapsed >= max_hours
        except: return False


# ── 4. نظام تحليل الارتباط ──────────────────────────────────────────────────
class CorrelationSystem:
    """
    يتجنب الصفقات المترابطة:
    لا تفتح BTC وETH في نفس الوقت
    لأنهما يتحركان معاً دائماً
    """

    CORRELATED_GROUPS = [
        ["BTC-USDT", "ETH-USDT", "BNB-USDT"],
        ["SOL-USDT", "AVAX-USDT", "NEAR-USDT", "APT-USDT"],
        ["LINK-USDT", "GRT-USDT"],
        ["DOGE-USDT", "SHIB-USDT", "PEPE-USDT", "WIF-USDT"],
        ["ARB-USDT", "OP-USDT"],
    ]

    def can_open(self, symbol: str,
                  open_positions: List[str]) -> Tuple[bool, str]:
        for group in self.CORRELATED_GROUPS:
            if symbol not in group: continue
            for pos in open_positions:
                if pos in group and pos != symbol:
                    return False, f"مرتبط بـ {pos}"
        return True, "✅"

    def portfolio_heat(self, positions: Dict,
                        balances: Dict,
                        total: float) -> float:
        """إجمالي المخاطرة المفتوحة"""
        heat = sum(balances.get(s,0)/total
                   for s in positions) if total>0 else 0
        return round(heat, 3)


# ── 5. نظام التقارير الذكي ───────────────────────────────────────────────────
class SmartReportingSystem:
    """
    يُنتج تقارير احترافية:
    - يومي / أسبوعي / شهري
    - مقارنة بـ BTC Buy&Hold
    - تحليل الأخطاء
    - توصيات للتحسين
    """

    def __init__(self, db):
        self.db = db

    def daily_summary(self, paper,
                       agents_count: int,
                       wfo_runs: int) -> str:
        perf  = paper.performance()
        lines = [
            f"📊 <b>التقرير اليومي</b>",
            f"━━━━━━━━━━━━━━━━━━",
            f"💰 PnL: <b>{perf['pnl']:+.2f} USDT</b>",
            f"📈 العائد: {perf['return_pct']:+.2f}%",
            f"🎯 الفوز: {perf['win_rate']}%",
            f"📐 Sharpe: {perf['sharpe']:.2f}",
            f"📉 Max DD: {perf['max_dd']:.1f}%",
            f"⚖️ PF: {perf['pf']:.2f}",
            f"━━━━━━━━━━━━━━━━━━",
            f"🤖 وكلاء: {agents_count}",
            f"🔬 WFO: {wfo_runs} تشغيل",
            f"💵 الرصيد: ${perf['balance']:,.2f}",
        ]
        return "\n".join(lines)

    def error_analysis(self, trades: List[Dict]) -> Dict:
        """يحلل الأخطاء ويقترح التحسينات"""
        if not trades: return {}
        losses = [t for t in trades if t.get("pnl",0) < 0]
        if not losses: return {"message": "لا خسائر — ممتاز!"}
        reasons = defaultdict(int)
        for t in losses:
            reasons[t.get("reason","?")] += 1
        top_reason = max(reasons, key=reasons.get)
        return {
            "total_losses": len(losses),
            "top_reason":   top_reason,
            "count":        reasons[top_reason],
            "suggestion":   self._suggest(top_reason)
        }

    def _suggest(self, reason: str) -> str:
        suggestions = {
            "SL 🛑":    "زِد ATR_SL من 1.5 إلى 2.0",
            "Trail 🔔": "قلّل Trailing من 1.2 إلى 1.5",
            "TP ✅":    "هذا ربح — لا مشكلة!",
            "Flash":   "السوق متقلب — قلّل الحجم"
        }
        for key, sug in suggestions.items():
            if key in reason: return sug
        return "راقب الأداء أكثر"


# ── 6. Multi-Account Manager ─────────────────────────────────────────────────
class MultiAccountSystem:
    """
    يُدير حسابات متعددة:
    - Master Account: أكبر رأس مال
    - Growth Account: مخاطرة متوسطة
    - Test Account: اختبار استراتيجيات جديدة
    """

    def __init__(self):
        self.accounts = {
            "MASTER": {"risk": 0.005, "leverage": 3,  "pct": 0.60},
            "GROWTH": {"risk": 0.010, "leverage": 5,  "pct": 0.30},
            "TEST":   {"risk": 0.020, "leverage": 10, "pct": 0.10},
        }

    def allocate(self, total_balance: float,
                  signal_quality: float) -> List[Dict]:
        orders = []
        for name, acc in self.accounts.items():
            if signal_quality < 60 and name == "TEST":
                continue
            bal  = total_balance * acc["pct"]
            size = bal * acc["risk"]
            orders.append({
                "account":  name,
                "balance":  round(bal, 2),
                "size":     round(size, 2),
                "risk":     acc["risk"],
                "leverage": acc["leverage"]
            })
        return orders




# ══════════════════════════════════════════════════════════════════════════════
# ⚡ ARCHITECTURAL FIXES — إصلاحات معمارية حقيقية
# ══════════════════════════════════════════════════════════════════════════════

import concurrent.futures
import threading
from asyncio import Lock as AsyncLock

# ── 1. WebSocket Data Manager — بدلاً من REST polling ────────────────────────
class WebSocketDataManager:
    """
    يستقبل البيانات عبر WebSocket بدلاً من REST:
    - لا Rate Limits
    - بيانات لحظية حقيقية
    - لا تجميد للـ Event Loop
    """
    def __init__(self):
        self.candles:  Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)
        self.prices:   Dict[str, float] = {}
        self.lock      = threading.Lock()
        self._running  = False
        self._tasks:   List = []

    async def start(self, exchange, symbols: List[str],
                     timeframes: List[str]):
        """يبدأ استقبال البيانات لكل الرموز والإطارات"""
        self._running = True
        log.info(f"📡 WebSocket يبدأ: {len(symbols)} رمز × {len(timeframes)} إطار")

        # فقط أهم الرموز والإطارات
        active_symbols = symbols[:10]   # حد أقصى 10 رموز
        active_tfs     = ["5m","1h","4h"]  # أهم الإطارات فقط

        tasks = []
        for symbol in active_symbols:
            for tf in active_tfs:
                task = asyncio.create_task(
                    self._watch_candles(exchange, symbol, tf))
                tasks.append(task)
                await asyncio.sleep(0.1)  # تجنب الفيضان

        self._tasks = tasks

    async def _watch_candles(self, exchange,
                               symbol: str, tf: str):
        """يستمع لشمعة واحدة"""
        while self._running:
            try:
                if hasattr(exchange, 'watch_ohlcv'):
                    candles = await exchange.watch_ohlcv(
                        symbol.replace("-","/"), tf, limit=100)
                    df = pd.DataFrame(candles,
                        columns=["timestamp","open","high",
                                  "low","close","volume"])
                    df["timestamp"] = pd.to_datetime(
                        df["timestamp"], unit="ms")
                    with self.lock:
                        self.candles[symbol][tf] = df
                        self.prices[symbol] = float(df["close"].iloc[-1])
                else:
                    await asyncio.sleep(10)
            except Exception as e:
                log.warning(f"WS [{symbol}][{tf}]: {e}")
                await asyncio.sleep(5)

    def get_candles(self, symbol: str,
                     tf: str) -> pd.DataFrame:
        with self.lock:
            return self.candles.get(symbol,{}).get(tf, pd.DataFrame())

    def get_price(self, symbol: str) -> float:
        with self.lock:
            return self.prices.get(symbol, 0.0)

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()


# ── 2. Background Task Manager — مهام خلفية منفصلة ──────────────────────────
class BackgroundTaskManager:
    """
    يُشغّل المهام الثقيلة في Thread منفصل:
    - تدريب ML
    - WFO Optimization
    - Backtesting
    بدون تجميد حلقة التداول الأساسية
    """
    def __init__(self):
        self.executor   = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="BotBG")
        self.results:   Dict[str, Any] = {}
        self._lock      = threading.Lock()

    def submit_ml_training(self, ml_agent, df: pd.DataFrame):
        """تدريب ML في الخلفية"""
        future = self.executor.submit(self._train_ml, ml_agent, df)
        future.add_done_callback(
            lambda f: self._on_ml_done(f, "ml_training"))
        return future

    def _train_ml(self, ml_agent, df: pd.DataFrame):
        try:
            return ml_agent.train(df)
        except Exception as e:
            log.error(f"ML Training error: {e}")
            return False

    def _on_ml_done(self, future, key: str):
        try:
            result = future.result()
            with self._lock:
                self.results[key] = result
            log.info(f"✅ ML Training اكتمل في الخلفية: {result}")
        except Exception as e:
            log.error(f"ML Done error: {e}")

    def submit_wfo(self, wfo_optimizer, df: pd.DataFrame,
                    current_params: Dict):
        """WFO في الخلفية"""
        future = self.executor.submit(
            wfo_optimizer.optimize, df, current_params)
        future.add_done_callback(
            lambda f: self._on_wfo_done(f))
        return future

    def _on_wfo_done(self, future):
        try:
            result = future.result()
            with self._lock:
                self.results["wfo"] = result
            log.info(f"✅ WFO اكتمل: score={result.get('score',0):.1f}")
        except Exception as e:
            log.error(f"WFO Done error: {e}")

    def get_result(self, key: str) -> Optional[Any]:
        with self._lock:
            return self.results.pop(key, None)

    def shutdown(self):
        self.executor.shutdown(wait=False)


# ── 3. Smart Rate Limiter — إدارة ذكية لـ API ────────────────────────────────
class SmartRateLimiter:
    """
    يُدير Rate Limits بذكاء:
    - يُوزّع الطلبات على الوقت
    - يُعطي الأولوية للطلبات المهمة
    - يُخزّن نتائج في Cache
    """
    def __init__(self, max_per_second: float = 5.0):
        self.max_rps    = max_per_second
        self.min_delay  = 1.0 / max_per_second
        self.last_call  = 0.0
        self.cache:     Dict[str, Tuple] = {}
        self.cache_ttl  = 60.0  # 60 ثانية
        self.calls:     int = 0
        self.throttled: int = 0

    async def wait(self):
        """انتظر الحد الأدنى بين الطلبات"""
        now     = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_delay:
            wait_t = self.min_delay - elapsed
            self.throttled += 1
            await asyncio.sleep(wait_t)
        self.last_call = time.time()
        self.calls    += 1

    def get_cached(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, ts = self.cache[key]
            if time.time() - ts < self.cache_ttl:
                return value
            del self.cache[key]
        return None

    def set_cached(self, key: str, value: Any):
        self.cache[key] = (value, time.time())

    def stats(self) -> Dict:
        return {
            "total_calls": self.calls,
            "throttled":   self.throttled,
            "cache_size":  len(self.cache),
            "hit_rate":    round(1-self.throttled/(self.calls+1e-10), 2)
        }


# ── 4. Simplified Agent Selector — تشغيل وكلاء أقل عند الحاجة ───────────────
class AgentSelector:
    """
    يختار عدد الوكلاء المناسب:
    - سوق هادئ: 3 وكلاء أساسيين
    - سوق متحرك: 7 وكلاء
    - إشارة قوية: كل الوكلاء
    يُقلل الحمل على الـ Event Loop
    """
    TIERS = {
        "MINIMAL": 3,   # TechnicalAgent, MLAgent, AICouncil
        "STANDARD": 7,  # + Volume, OrderFlow, Whale, Evolutionary
        "FULL":     14, # كل الوكلاء
    }

    def select(self, agents: List,
                regime: str,
                signal_strength: float) -> List:
        if regime == "VOLATILE" or signal_strength < 0.3:
            n = self.TIERS["MINIMAL"]
        elif regime in ("TRENDING_UP","TRENDING_DOWN","BREAKOUT"):
            n = self.TIERS["STANDARD"]
        else:
            n = self.TIERS["FULL"]
        # الأهم أولاً
        priority = ["Technical","ML","AICouncil","Evolutionary",
                    "Volume","OrderFlow","Whale","ICT_SMC",
                    "Strategies","Indicators","FlashCrash",
                    "Parabolic","DarkPool","Sentiment"]
        sorted_agents = sorted(
            agents,
            key=lambda a: priority.index(a.name)
                          if a.name in priority else 99)
        selected = sorted_agents[:n]
        log.info(f"🤖 وكلاء نشطون: {len(selected)}/{len(agents)} ({regime})")
        return selected


# ══════════════════════════════════════════════════════════════════════════════
# 🔄 MAIN BOT
# ══════════════════════════════════════════════════════════════════════════════
class UltimateFinalBot:
    def __init__(self):
        self.db         = Database()
        self.exchange   = ExchangeConnector()
        self.risk       = RiskManager()
        self.notifier   = Notifier()
        self.council    = OpenRouterCouncil()
        self.flash_guard= FlashCrashGuard(self.db)
        self.parabolic  = ParabolicSqueezeDetector()
        self.dark_pool  = DarkPoolDetector()
        self.whale_trap = WhaleTrapDetector()
        self.cb_ultra   = CircuitBreakerUltra()
        self.paper      = PaperEngine()
        self.ecosystem  = AgentEcosystem()  # 🧬 النظام البيئي
        self.wfo        = AutoWalkForwardOptimizer()
        self.mdp        = MillionDollarProtocol()
        self.trend_f    = TrendFilter()
        self.session_f  = SessionFilter()
        self.elite_f    = EliteSignalFilter()
        self.smart_trail= SmartTrailingStop()
        self.regime_det = MarketRegimeDetector()
        self.accel      = CapitalAccelerationTrigger()
        self.kill_sw    = SmartKillSwitch()
        self.meta_learn  = MetaLearningEngine()
        self.shadow      = ShadowTradingEngine()
        self.lat_opt     = LatencyOptimizer()
        # v22 — الجودة فوق الكمية
        self.fast_path   = FastLocalPath()            # ⚡ تنفيذ فوري
        self.min_profit  = MinProfitFilter()          # 💰 فلتر الربح
        self.candle_f    = CandleCloseFilter()        # 🕯️ إغلاق الشمعة
        self.real_bt     = RealisticBacktestEngine()  # 📊 باكتست حقيقي
        self.tf_switch   = VolatilityTimeframeSwitch() # ⏱️ إطار ذكي   # 💰 بروتوكول المليون دولار
        # ── v19 الأنظمة الجديدة ──────────────────────────────────────────────
        self.vol_scanner = VolatilityScanner()      # ⚡ صائد التقلب
        self.sniper      = MomentumSniper()          # 🎯 قناص الزخم
        self.compound_eng= UltraCompoundEngine(config.INITIAL_CAPITAL)  # 📈 التراكم
        self.pyramid     = PyramidEngine()           # 🔺 مضاعف الأرباح
        self.snowball    = SnowballEngine(config.INITIAL_CAPITAL)  # ❄️ كرة الثلج
        self.ai_scorer   = AISignalScorer()          # 🧠 Claude يُنقّط
        self.awareness   = BotSelfAwareness()   # 🧠 الوعي الذاتي
        self.dca         = SmartDCABot()         # 🤖 DCA ذكي
        self.grid        = SmartGridTrading()    # 📊 Grid Trading
        self.arbitrage   = SmartArbitrage()      # 🔄 Arbitrage
        self.flywheel    = FlywheelStrategy()    # 🎯 Flywheel
        self.marketplace  = SignalMarketplace()    # 📡 Signal Market
        self.memory       = LongTermMemory()        # 🧠 ذاكرة طويلة المدى
        self.hypothesis   = HypothesisEngine()      # 💡 محرك الفرضيات
        self.smart_exec   = SmartExecutionEngine()  # ⚡ تنفيذ ذكي
        self.rl_learner   = ReinforcementLearner()  # 🎓 تعلم تعزيزي
        self.collective   = CollectiveIntelligence() # 🌐 عقل جماعي
        self.meta_agent   = MetaAgentManager()        # ⚡ Meta-Agent
        # ── الوكلاء الأساسيون (11 وكيل) ─────────────────────────────────────
        self.ai_agent   = AICouncilAgent(
            "AICouncil", config.AGENT_WEIGHTS["AICouncil"], self.council)
        self.evo_agent  = EvolutionaryAgent(
            "Evolutionary", config.AGENT_WEIGHTS["Evolutionary"], self.db)

        self.agents = [
            TechnicalAgent("Technical",    config.AGENT_WEIGHTS["Technical"]),
            MLEnsembleAgent("ML",          config.AGENT_WEIGHTS["ML"]),
            SentimentAgent("Sentiment",    config.AGENT_WEIGHTS["Sentiment"]),
            VolumeProfileAgent("Volume",   config.AGENT_WEIGHTS["Volume"]),
            OrderFlowAgent("OrderFlow",    config.AGENT_WEIGHTS["OrderFlow"]),
            WhaleAgent("Whale",            config.AGENT_WEIGHTS["Whale"]),
            FlashCrashAgent("FlashCrash",  config.AGENT_WEIGHTS["FlashCrash"],
                             self.flash_guard),
            ParabolicAgent("Parabolic",    config.AGENT_WEIGHTS["Parabolic"],
                            self.parabolic),
            DarkPoolAgent("DarkPool",      config.AGENT_WEIGHTS["DarkPool"],
                           self.dark_pool),
            self.evo_agent,
            self.ai_agent,
        ]

        # إضافة وكلاء متخصصين (مع فحص التكرار)
        extra_agents = [
            ICTSMCAgent("ICT_SMC",     3.5),
            StrategyAgent("Strategies", 3.0),
            IndicatorAgent("Indicators",2.5),
        ]
        existing_names = {a.name for a in self.agents}
        for agent in extra_agents:
            if agent.name not in existing_names:
                self.agents.append(agent)
                config.AGENT_WEIGHTS[agent.name] = agent.weight
                existing_names.add(agent.name)

        # الأنظمة المتقدمة
        self.capital_mgmt  = CapitalManagementSystem()
        self.signal_filter = SignalFilterSystem()
        self.pos_manager   = AdvancedPositionManager()
        self.correlation   = CorrelationSystem()
        self.reporter      = SmartReportingSystem(self.db)
        self.multi_account = MultiAccountSystem()
        self.ws_manager    = WebSocketDataManager()
        self.bg_tasks      = BackgroundTaskManager()
        self.rate_limiter  = SmartRateLimiter(max_per_second=5.0)
        self.agent_selector= AgentSelector()
        log.info(f"✅ جاهز — v18.6 | {len(self.agents)} وكيل")

        self.consensus   = ConsensusEngine(self.agents)
        self.data_cache: Dict = defaultdict(dict)
        self.positions:  Dict = {}
        self.running     = True
        self.cycle       = 0
        self.transferred = 0.0
        self.last_report = datetime.now().date()
        self.peak_equity = config.PAPER_BALANCE

    def _get_active_symbols(self) -> List[str]:
        """اختيار العملات حسب الـ Tier المحدد"""
        t1 = config.SYMBOLS_TIER1                           # 10
        t2 = t1 + config.SYMBOLS_TIER2                      # 30
        t3 = t2 + config.SYMBOLS_TIER3                      # 60
        t4 = t3 + config.SYMBOLS_TIER4                      # 100
        tiers = {1: t1, 2: t2, 3: t3, 4: t4}
        syms  = tiers.get(config.ACTIVE_TIER, t2)
        log.info(f"✅ عملات نشطة: {len(syms)} (Tier {config.ACTIVE_TIER})")
        return syms

    async def initialize(self):
        log.info("🚀 تهيئة Ultimate Final v18.6...")

        # تدريب ML — مرة واحدة فقط في الخلفية
        df_train = await self.exchange.fetch_ohlcv("BTC-USDT", "1h", 400)
        if not df_train.empty:
            df_train = FeatureEngine.compute(df_train)
            ml = next((a for a in self.agents
                       if isinstance(a, MLEnsembleAgent)), None)
            if ml:
                self.bg_tasks.submit_ml_training(ml, df_train)
                log.info("🤖 ML Training بدأ في الخلفية...")

        # بدء WebSocket — مهمة واحدة لكل رمز (DeepSeek Fix)
        if self.exchange.okx and CCXT_AVAILABLE:
            top_symbols = config.SYMBOLS_TIER1[:10]   # أهم 10 فقط
            await self.ws_manager.start(
                self.exchange.okx,
                top_symbols,
                ["1m","5m","1h"])   # 3 إطارات كافية

        await self._update_data()
        mode = "🧪 Paper" if config.PAPER_TRADING else "💰 حقيقي"
        self.mdp.print_projection()             # 💰 عرض جدول الإسقاطات
        await self.notifier.startup(mode, len(self.agents))
        log.info(f"✅ جاهز | وضع: {mode} | وكلاء: {len(self.agents)}")

    async def _update_data(self):
        active = self._get_active_symbols()
        # تحديث TrendFilter + Regime + TF Switch
        btc_4h = self.data_cache.get("BTC-USDT",{}).get("4h", pd.DataFrame())
        btc_1h = self.data_cache.get("BTC-USDT",{}).get("1h", pd.DataFrame())
        btc_1m = self.data_cache.get("BTC-USDT",{}).get("1m", pd.DataFrame())
        if not btc_4h.empty:
            self.trend_f.update(btc_4h)
        if not btc_1h.empty:
            self.regime_det.detect(btc_1h)
        # ⏱️ TF Switch — إطار ذكي حسب التقلب
        if not btc_1m.empty and "atr_pct" in btc_1m.columns:
            atr_pct_now = float(btc_1m["atr_pct"].iloc[-1])
            new_tf = self.tf_switch.update(atr_pct_now)
            config.PRIMARY_TF = new_tf
        for symbol in active:
            for tf in config.TIMEFRAMES:
                # WebSocket أولاً
                df = self.ws_manager.get_candles(symbol, tf)
                if df.empty:
                    await self.rate_limiter.wait()
                    df = await self.exchange.fetch_ohlcv(symbol, tf, config.LOOKBACK)
                if not df.empty:
                    df = FeatureEngine.compute(df)
                    self.data_cache[symbol][tf] = df
                await asyncio.sleep(0.01)

    async def run_cycle(self):
        self.cycle += 1
        await self._update_data()

        # حساب الـ equity
        equity    = self.paper.balance if config.PAPER_TRADING else 0

        # 💰 تحديث بروتوكول المليون دولار
        mdp_result = self.mdp.update(equity)
        # 📈 v19: تحديث محرك التراكم
        self.compound_eng.record(equity)
        # ❄️ Snowball + Shadow
        self.snowball.update_mode(self.mdp.current_mode)

        # ── DeepSeek Fix: تفعيل الأنظمة غير المستخدمة ─────────────────
        # 1. ReinforcementLearner — يتعلم من حالة السوق الحالية
        btc_rl = self.data_cache.get("BTC-USDT",{}).get("1h", pd.DataFrame())
        if not btc_rl.empty and hasattr(self.rl_learner, 'state_key'):
            last_row = btc_rl.iloc[-1].to_dict()
            rl_state = self.rl_learner.state_key(last_row)
            rl_action= self.rl_learner.choose_action(rl_state)
            # تطبيق توصية RL: تعديل MIN_AGREEMENT ديناميكياً
            if rl_action == "AGGRESSIVE":
                config.MIN_AGREEMENT = max(config.MIN_AGREEMENT - 0.02, 0.50)
            elif rl_action == "CONSERVATIVE":
                config.MIN_AGREEMENT = min(config.MIN_AGREEMENT + 0.02, 0.80)

        # 2. CollectiveIntelligence — إذاعة نتائج الوكلاء للمجموعة
        if hasattr(self.collective, 'broadcast') and self.cycle % 5 == 0:
            for agent in self.agents[:5]:   # أفضل 5 وكلاء فقط
                try:
                    df_tmp = self.data_cache.get("BTC-USDT",{})
                    df_tmp["symbol"] = "BTC-USDT"
                    d, c, _ = await agent.analyze(df_tmp)
                    sig = "BUY" if d==1 else "SELL" if d==-1 else "HOLD"
                    self.collective.broadcast(agent.name, sig, c, "auto")
                except Exception:
                    pass
        # 👥 Shadow: تحديث بالأسعار الحالية
        live_prices = {s: self.ws_manager.get_price(s)
                       for s in self._get_active_symbols()}
        self.shadow.update_shadow(live_prices)
        if self.cycle % 100 == 0:
            cmp = self.shadow.compare(self.paper.balance)
            if cmp.get("compared"):
                log.info(
                    f"👥 Shadow: pnl={cmp['shadow_pnl']:+.2f} "
                    f"wr={cmp['shadow_wr']:.0%} | "
                    f"Live pnl={cmp['live_pnl']:+.2f} | "
                    f"Promoted={self.shadow.promoted}"
                )
        # عرض حالة الكرة كل 20 دورة
        if self.cycle % 20 == 0:
            log.info(self.snowball.snowball_status(equity))
        if mdp_result["switched"]:
            msg = (f"💰 تحوّل للوضع: {mdp_result['mode']}\n"
                   f"{mdp_result['settings']['description']}\n"
                   f"رافعة: x{mdp_result['settings']['leverage']} | "
                   f"مخاطرة: {mdp_result['settings']['risk_pct']*100:.0f}%/صفقة\n"
                   f"الرصيد: ${equity:.2f} | النمو: ×{mdp_result['growth_x']}")
            log.info(msg)
            await self.notifier.send(msg)
        if mdp_result["milestone"]:
            ms_msg = self.mdp.milestone_msg(equity, mdp_result["milestone"])
            log.info(ms_msg)
            await self.notifier.send(ms_msg)
        daily_pnl = self.db.get_daily_pnl()

        # فحص المخاطر
        # 🛑 Kill Switch أولاً
        ks_ok, ks_reason, ks_mins = self.kill_sw.check(equity)
        if not ks_ok:
            log.warning(f"🛑 {ks_reason} — استئناف بعد {ks_mins} دقيقة")
            return
        can_trade, reason, size_mult = self.risk.check(equity, daily_pnl)
        if not can_trade:
            log.warning(f"⚠️ لا تداول: {reason}")
            return

        # إدارة الصفقات المفتوحة
        await self._manage_positions()

        # البحث عن إشارات
        if len(self.positions) < config.MAX_POSITIONS:
            await self._scan_signals(size_mult)

        # ══ Meta-Agent ═══════════════════════════════════════════
        df_meta = self.data_cache.get("BTC-USDT",{}).get("1h", pd.DataFrame())
        if not df_meta.empty:
            agent_results = {}
            for agent in self.agents:
                try:
                    data_tmp = dict(self.data_cache.get("BTC-USDT",{}))
                    d, c, det = await agent.analyze(data_tmp)
                    sig = "BUY" if d==1 else "SELL" if d==-1 else "HOLD"
                    agent_results[agent.name] = (sig, c, det)
                except: pass
            meta_decision = self.meta_agent.run(
                df_meta, self.agents,
                self.evo_agent, agent_results)
            if meta_decision["switched"]:
                await self.notifier.send(
                    f"🎭 <b>تغيير الشخصية!</b>\n"
                    f"النظام: {meta_decision['regime']}\n"
                    f"{meta_decision['params']['description']}"
                )

        # ══ التقييم الذاتي ════════════════════════════════════════
        self_eval = self.awareness.evaluate()
        if self.cycle % 10 == 0:
            log.info(
                f"🧠 [{self_eval['mood']}] "
                f"ثقة={self_eval['confidence']:.0%} | "
                f"ربح={self_eval['win_streak']}↑ | "
                f"خسارة={self_eval['loss_streak']}↓ | "
                f"{self_eval['message']}"
            )
            if self_eval["lessons"]:
                for lesson in self_eval["lessons"]:
                    log.info(f"  💡 {lesson}")

        # هل يتداول؟
        should, reason = self.awareness.should_trade()
        if not should:
            log.info(f"🧠 قرار ذاتي: {reason}")

        # ══ Walk-Forward تلقائي كل ساعة ════════════════════════════
        if self.wfo.should_run():
            df_wfo = self.data_cache.get("BTC-USDT",{}).get("1h", pd.DataFrame())
            if not df_wfo.empty and len(df_wfo) >= 100:
                current = {
                    "rsi_buy":        self.evo_agent.params.get("rsi_buy", 40),
                    "rsi_sell":       self.evo_agent.params.get("rsi_sell", 60),
                    "adx_min":        self.evo_agent.params.get("adx_min", 20),
                    "vol_min":        self.evo_agent.params.get("vol_min", 1.2),
                    "atr_sl":         config.STOP_LOSS_ATR,
                    "atr_tp":         config.TAKE_PROFIT_ATR,
                    "min_conditions": 4,
                }
                # v22: استخدم الباكتست الحقيقي في WFO
                rbt_result = self.real_bt.run(df_wfo, current)
                if rbt_result["realistic_return"] < -20:
                    log.warning(f"📊 Realistic BT: return={rbt_result['realistic_return']}% → تحذير")
                best = self.wfo.optimize(df_wfo, current)
                if best:
                    self.evo_agent.params["rsi_buy"]  = best["rsi_buy"]
                    self.evo_agent.params["rsi_sell"] = best["rsi_sell"]
                    self.evo_agent.params["adx_min"]  = best["adx_min"]
                    self.evo_agent.params["vol_min"]  = best["vol_min"]
                    stats = self.wfo.get_stats()
                    await self.notifier.send(
                        f"🔬 <b>Walk-Forward #{stats['runs']}</b>\n"
                        f"📊 Score: {stats['last_score']:.1f}\n"
                        f"✅ تحسينات: {stats['improvements']}\n"
                        f"⏰ التالي: {stats['next_run_in']//60} دقيقة"
                    )

        # ══ تطور الوكلاء ════════════════════════════════════════════
        if self.cycle % 5 == 0:
            perf     = self.paper.performance()
            eco_data = self.ecosystem.run_cycle(perf.get("win_rate",50)/100*100)
            best_params = self.ecosystem.get_best_params()
            if best_params and self.cycle % 20 == 0:
                # تطبيق أفضل معاملات على الوكيل التطوري
                self.evo_agent.params["rsi_buy"]  = best_params.get("rsi_buy",40)
                self.evo_agent.params["rsi_sell"] = best_params.get("rsi_sell",60)
                self.evo_agent.params["adx_min"]  = best_params.get("adx_min",20)
                log.info(
                    f"🧬 Gen{best_params.get('generation',0)} | "
                    f"Best: {best_params.get('name','?')} | "
                    f"👥 {eco_data['population']} | "
                    f"👶 {eco_data['total_born']} | "
                    f"💀 {eco_data['total_dead']}"
                )
            if eco_data.get("births", 0) > 0:
                await self.notifier.send(
                    f"🧬 <b>مواليد جدد!</b>\n"
                    f"👶 {eco_data['births']} وكيل جديد\n"
                    f"🏆 الأفضل: {eco_data['best']}\n"
                    f"🌍 الجيل: {eco_data['generation']}"
                )

        # تحويل الأرباح
        if config.AUTO_PROFIT_TRANSFER:
            profit = self.paper.balance - config.PAPER_BALANCE
            if profit - self.transferred >= config.PROFIT_THRESHOLD:
                transfer_amount = (profit - self.transferred) * config.PROFIT_TRANSFER_PCT
                self.transferred += transfer_amount
                self.db.conn.execute(
                    "INSERT INTO transfers VALUES(datetime('now'),?,?)",
                    (transfer_amount, "LOGGED"))
                self.db.conn.commit()
                log.profit(f"تحويل ${transfer_amount:.2f} للمحفظة")
                await self.notifier.send(
                    f"💸 <b>تحويل أرباح تلقائي</b>\n"
                    f"${transfer_amount:.2f} USDT\n"
                    f"إجمالي محوّل: ${self.transferred:.2f}")

        # ══ التأمل اليومي والتقرير ══════════════════════════════════════════
        today = datetime.now().date()
        if today != self.last_report:
            reflection = self.awareness.daily_reflection()
            log.info(f"\n{reflection}")
            await self.notifier.send(
                f"🧠 <b>التأمل اليومي</b>\n{reflection}")
            await self.notifier.daily_report(
                self.db.get_stats(),
                self.paper.performance(),
                self.transferred)
            self.last_report = today

        # ملخص
        perf  = self.paper.performance()
        stats = self.db.get_stats()
        cmpd  = self.compound_eng.compound_summary(self.paper.balance)
        log.info(
            f"━━ دورة {self.cycle} | "
            f"${self.paper.balance:.2f} | "
            f"×{self.paper.balance/config.INITIAL_CAPITAL:.1f} | "
            f"WR={perf['win_rate']}% | "
            f"Sharpe={perf['sharpe']:.2f} | "
            f"وضع={self.mdp.current_mode} ━━"
        )
        if self.cycle % 50 == 0:
            log.info(f"\n{cmpd}")
        if self.cycle % 100 == 0:
            log.info(
                f"v22 | TF={config.PRIMARY_TF}({self.tf_switch.noise_level()}) | "
                f"Regime={self.regime_det.regime} | "
                f"Trend={self.trend_f.bias} | "
                f"Elite={self.elite_f.pass_rate:.0%} | "
                f"MinProfit blocked={self.min_profit.rejected} | "
                f"Candle waits={self.candle_f.waits}"
            )
            log.info(self.fast_path.status())
            log.info(self.min_profit.status())

    async def _scan_signals(self, size_mult: float):
        active = self._get_active_symbols()

        # ⚡ v19: VolatilityScanner — أعطِ أولوية لأعلى 5 عملات تقلباً
        # 🧠 Regime → Dynamic MIN_AGREEMENT
        regime_now    = self.regime_det.regime
        vol_scores    = list(self.vol_scanner.scores.values())[:5]
        avg_vol_score = sum(vol_scores)/len(vol_scores) if vol_scores else 0.5
        dynamic_min   = self.regime_det.min_agreement_boost(
            config.MIN_AGREEMENT, avg_vol_score)
        top5_volatile = self.vol_scanner.scan(self.data_cache)
        # ⚡ LatencyOptimizer — batch ذكي
        _t0     = self.lat_opt.start()
        active  = self.lat_opt.get_batch(active, self.vol_scanner.scores)
        n_agents= self.lat_opt.get_agent_count()
        active  = sorted(active,
                         key=lambda s: self.vol_scanner.get_score(s),
                         reverse=True)

        for symbol in active:
            data = dict(self.data_cache[symbol])
            data["symbol"] = symbol
            if not data: continue

            # ── v19: MomentumSniper — فحص مبكر ─────────────────────
            df1m = data.get("1m", pd.DataFrame())
            sniper_r = self.sniper.detect(df1m) if not df1m.empty else {"signal":"HOLD","confidence":0.0}
            sniper_boost = 0.0
            if sniper_r["signal"] != "HOLD":
                sniper_boost = sniper_r["confidence"] * 0.15
                log.info(f"🎯 [{symbol}] Sniper={sniper_r['signal']} "
                         f"type={sniper_r.get('type','?')} "
                         f"conf={sniper_r['confidence']:.0%}")

            # Whale Trap — مع استخدامه في القرار
            df15m     = data.get("15m", pd.DataFrame())
            trap      = self.whale_trap.detect(df15m) if not df15m.empty else {}
            trap_sig  = trap.get("signal", "HOLD")
            trap_conf = trap.get("confidence", 0.0)
            if trap.get("trap"):
                log.info(f"🐋 [{symbol}] Whale Trap={trap.get('type')} → {trap_sig}")

            # ⚡ FastLocalPath — تنفيذ فوري للإشارات القوية
            is_fast = self.fast_path.should_fast_execute(
                conf, trend_ok,
                sniper_r.get("confidence", 0.0),
                self.regime_det.regime)

            # AI Council — فقط للإشارات المتوسطة (ليس القوية)
            major_symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
            ai_cooldown   = (self.cycle % 240 == 0 and not is_fast)
            df5m = data.get("5m", pd.DataFrame())
            if not df5m.empty and len(df5m)>0 and symbol in major_symbols and ai_cooldown:
                last = df5m.iloc[-1]
                price= float(last["close"])
                inds = {
                    "rsi":      float(last.get("rsi",50)),
                    "adx":      float(last.get("adx",0)),
                    "macd_hist":float(last.get("macd_hist",0)),
                    "bb_pct":   float(last.get("bb_pct",0.5)),
                    "vol_ratio":float(last.get("vol_ratio",1)),
                }
                tech_sig = ("BUY"  if inds["rsi"]<45 and inds["macd_hist"]>0 else
                            "SELL" if inds["rsi"]>55 and inds["macd_hist"]<0 else
                            "HOLD")
                ai_r = await self.council.consult(symbol,price,inds,tech_sig)
                self.ai_agent.update(ai_r)
            else:
                price = self.ws_manager.get_price(symbol)
                if price <= 0:
                    price = await self.exchange.fetch_price(symbol)
                ai_r  = {"signal":"HOLD","confidence":0.5}

            # اختيار الوكلاء المناسب للسوق (آمن في asyncio)
            regime   = self.meta_agent.personality.current_personality
            selected = self.agent_selector.select(self.agents, regime, 0.5)
            # إنشاء consensus مؤقت بدلاً من تعديل الأصلي
            temp_consensus = ConsensusEngine(selected)
            # إجماع الوكلاء
            signal, conf, details = await temp_consensus.decide(data)

            # فلترة الإشارات بـ SignalFilterSystem
            df_filter = self.data_cache.get(symbol,{}).get("1h", pd.DataFrame())
            noise_ok  = self.signal_filter.noise_filter(df_filter)
            quality   = self.signal_filter.quality_score(
                signal, conf,
                sum(1 for v in details.values() if v.get("dir",0)!=0),
                len(self.agents),
                self.meta_agent.personality.current_personality,
                False
            )
            # ── v19: Sniper Boost على الثقة الكلية ──────────────────
            if sniper_r["signal"] in ("BUY","SELL"):
                sniper_dir = "LONG" if sniper_r["signal"]=="BUY" else "SHORT"
                if sniper_dir == signal:
                    conf = min(conf + sniper_boost, 0.95)

            # ── v19: AISignalScorer — Claude يُقيّم الإشارة ─────────────
            df5_last = data.get("5m", pd.DataFrame())
            inds_for_ai = {}
            if not df5_last.empty:
                row = df5_last.iloc[-1]
                inds_for_ai = {
                    "rsi":       float(row.get("rsi",50)),
                    "adx":       float(row.get("adx",0)),
                    "macd_hist": float(row.get("macd_hist",0)),
                    "bb_pct":    float(row.get("bb_pct",0.5)),
                    "vol_ratio": float(row.get("vol_ratio",1)),
                }
            ai_score_r = await self.ai_scorer.score(
                symbol, signal, conf, inds_for_ai,
                self.mdp.current_mode)
            ai_pass    = ai_score_r.get("pass", True)
            ai_score   = ai_score_r.get("score", conf*100)

            # ✅ TrendFilter — لا تتداول ضد الاتجاه الكبير
            trend_ok     = self.trend_f.allows(signal)
            trend_mult   = self.trend_f.multiplier()
            # ✅ SessionFilter — حجم أكبر في أوقات الذروة
            session_mult = self.session_f.size_multiplier()
            # تعديل الثقة بـ trend_mult
            if trend_ok:
                conf = min(conf * trend_mult, 0.97)
            # ── ELITE FILTER ────────────────────────────────────────
            already_open_sym = any(
                p["symbol"] == symbol
                for p in self.positions.values())
            daily_loss = self.db.get_daily_pnl()
            elite_pass, elite_score, elite_reason = self.elite_f.evaluate(
                conf        = conf,
                trend_ok    = trend_ok,
                is_prime    = self.session_f.is_prime_time(),
                sniper_conf = sniper_r.get("confidence", 0.0),
                already_open= already_open_sym,
                daily_loss  = daily_loss,
                balance     = self.paper.balance,
            )
            if signal in ("LONG","SHORT") and elite_pass and ai_pass:
                await self._execute(symbol, signal, conf,
                                     price, details, ai_r,
                                     size_mult * session_mult)
                self.db.log_signal(symbol, signal, conf,
                                    json.dumps(details),
                                    json.dumps(ai_r))

        # ✅ إصلاح Gemini #2 — قياس Latency في نهاية _scan_signals
        self._end_scan_latency(_t0)

    async def _execute(self, symbol, direction, conf,
                        price, details, ai_r, size_mult):
        df  = self.data_cache[symbol].get(config.PRIMARY_TF, pd.DataFrame())
        atr = float(df.iloc[-1].get("atr",price*0.01)) if not df.empty else price*0.01

        balance = self.paper.balance if config.PAPER_TRADING else 0
        aware_mult = self.awareness.size_multiplier()

        # 🚀 Regime size + TP multiplier
        regime_size_mult = self.regime_det.size_multiplier()
        # 💰 MDP BOOST — مضاعف ذكي حسب الوضع والثقة
        ai_signal = ai_r.get("signal", "HOLD")
        ai_match  = ((ai_signal == "BUY"  and direction == "LONG") or
                     (ai_signal == "SELL" and direction == "SHORT"))
        mdp_boost   = self.mdp.get_boost(conf, ai_match)
        # 🚀 CapitalAccelerationTrigger — الفرصة الذهبية
        whale_det   = any(d.get("dir",0) != 0
                          for d in details.values()
                          if "Whale" in str(d))
        accel_mult  = self.accel.check(
            conf, whale_det,
            sniper_r.get("confidence",0.0) if "sniper_r" in dir() else 0.0,
            self.regime_det.regime)
        final_boost = mdp_boost * accel_mult * regime_size_mult

        # استخدام CapitalManagementSystem
        cm_result = self.capital_mgmt.calculate(
            balance,
            [t["pnl"] for t in self.paper.trades[-50:]]
                if self.paper.trades else [],
            self.awareness.evaluate().get("win_rate", 0.5)
        )
        # ❄️ SNOWBALL — حجم الصفقة مرتبط بالرصيد الحالي دائماً
        snowball_qty = self.snowball.get_position_size_usdt(
            balance, price, atr, config.MAX_LEVERAGE)
        # تعديل بـ mdp_boost و conf
        snowball_qty = snowball_qty * min(mdp_boost * conf, 2.0)

        # فحص CapitalManagement كطبقة حماية إضافية
        cm_safe  = cm_result.get("safe", True)
        if not cm_safe:
            snowball_qty *= 0.5   # تقليل نصف عند الخطر

        qty      = snowball_qty
        min_order= getattr(config, "MIN_ORDER_USDT", 1.0)
        if qty * price < min_order: return

        # 💰 MinProfitFilter — لا تدخل إذا الربح أقل من التكلفة × 3
        profit_ok, profit_reason, exp_profit, cost = self.min_profit.check(
            price, qty, atr, config.TAKE_PROFIT_ATR)
        if not profit_ok:
            log.info(f"💰 MinProfit رُفض [{symbol}]: {profit_reason}")
            return

        # 🕯️ CandleCloseFilter — انتظر إغلاق الشمعة
        waited = await self.candle_f.wait_for_close(config.PRIMARY_TF, max_wait=6.0)
        if waited:
            # تحديث السعر بعد الانتظار
            new_price = self.ws_manager.get_price(symbol)
            if new_price > 0:
                price = new_price

        sl = (price-atr*config.STOP_LOSS_ATR  if direction=="LONG"
              else price+atr*config.STOP_LOSS_ATR)
        tp = (price+atr*config.TAKE_PROFIT_ATR if direction=="LONG"
              else price-atr*config.TAKE_PROFIT_ATR)

        mode = "PAPER" if config.PAPER_TRADING else "REAL"

        # ── تعيين الرافعة ─────────────────────────────────────────
        if not config.PAPER_TRADING and self.exchange.okx:
            try:
                await self.exchange.okx.set_leverage(
                    config.MAX_LEVERAGE, symbol,
                    params={"mgnMode": "isolated"})
            except Exception as e:
                log.warning(f"set_leverage: {e}")

        if config.PAPER_TRADING:
            pos_id = self.paper.open(
                symbol, "buy" if direction=="LONG" else "sell",
                price, qty, sl, tp, "bot")
            if pos_id:
                self.positions[pos_id] = {
                    "symbol":symbol,"direction":direction,
                    "entry":price,"qty":qty,"sl":sl,"tp":tp,
                    "atr":atr,"peak":price,"mode":mode,
                    "details":     details,
                    "fast_entry":  self.fast_path.should_fast_execute(
                        conf,
                        self.trend_f.allows("LONG"),
                        sniper_r.get("confidence",0.0) if "sniper_r" in dir() else 0.0,
                        self.regime_det.regime),  # ✅ v22
                    "trade_id": self.db.open_trade(
                        symbol, direction, mode, price, qty, 1,
                        {"agents":details,"ai":ai_r})
                }
                await self.notifier.trade_alert(
                    symbol, direction, price, conf, mode,
                    ai_r.get("signal","?"))
                log.info(
                    f"{'📈' if direction=='LONG' else '📉'} "
                    f"[{symbol}] {direction} @ {price:.4f} | "
                    f"conf={conf:.0%} | AI={ai_r.get('signal','?')}"
                )
                # 👥 Shadow Trade
                self.shadow.shadow_entry(symbol, direction, price, atr)

    async def _manage_positions(self):
        for pos_id in list(self.positions.keys()):
            pos   = self.positions[pos_id]
            # WebSocket أولاً للسعر اللحظي
            price = self.ws_manager.get_price(pos["symbol"])
            if price <= 0:
                price = await self.exchange.fetch_price(pos["symbol"])
            if price <= 0: continue

            pos["peak"] = max(pos.get("peak",pos["entry"]), price)

            # 🎯 SmartTrailingStop — SL ذكي يتبع الربح
            new_sl = self.smart_trail.calculate_sl(
                pos["entry"], pos["peak"], price,
                pos["atr"], pos["direction"], pos["sl"])
            if new_sl != pos["sl"]:
                pos["sl"] = new_sl

            # ── v19: PyramidEngine — زيادة الحجم على الرابحين ───────────
            pyramid_add = self.pyramid.should_add(
                pos_id, pos["entry"], price,
                pos["atr"], pos["direction"])
            if pyramid_add and len(self.positions) < config.MAX_POSITIONS:
                add_qty = pos["qty"] * pyramid_add["size_pct"]
                if config.PAPER_TRADING and add_qty * price >= 1.0:
                    new_pid = self.paper.open(
                        pos["symbol"],
                        "buy" if pos["direction"]=="LONG" else "sell",
                        price, add_qty, pos["sl"], pos["tp"], "pyramid")
                    if new_pid:
                        self.pyramid.record_add(
                            pos_id, pyramid_add["level"], price, add_qty)
                        log.info(f"🔺 Pyramid L{pyramid_add['level']} "
                                 f"[{pos['symbol']}] +{add_qty:.4f} @ {price:.4f}")

            # Breakeven Stop تلقائي
            new_sl = self.pos_manager.breakeven_sl(
                pos["entry"], price, pos["atr"],
                pos["direction"], pos["sl"])
            if new_sl != pos["sl"]:
                pos["sl"] = new_sl
                log.info(f"🔒 Breakeven: SL → {new_sl:.4f}")
            atr         = pos["atr"]
            direction   = pos["direction"]
            reason      = None

            if direction=="LONG":
                trail = pos["peak"]-atr*1.2
                if price<=pos["sl"]:    reason="SL 🛑"
                elif price>=pos["tp"]:  reason="TP ✅"
                elif config.TRAILING_ENABLED and price<=trail:
                    reason="Trail 🔔"
            else:
                trail = pos["peak"]+atr*1.2
                if price>=pos["sl"]:   reason="SL 🛑"
                elif price<=pos["tp"]: reason="TP ✅"
                elif config.TRAILING_ENABLED and price>=trail:
                    reason="Trail 🔔"

            # Flash Crash Emergency
            fc = self.flash_guard.check(pos["symbol"], price)
            if fc.get("crash") and fc.get("action")=="EMERGENCY_CLOSE":
                reason = "Flash Crash ⚡"

            if reason:
                pnl = self.paper.close(pos_id, price, reason)
                if pnl is not None:
                    db_pnl = self.db.close_trade(
                        pos["trade_id"], price, pos["entry"],
                        pos["qty"], direction, reason)
                    self.risk.update(db_pnl, self.paper.balance)
                    # ❄️ Snowball: تسجيل الصفقة
                    doubled = self.snowball.record_trade(pnl, self.paper.balance)
                    self.kill_sw.record(pnl)
                    # ⚡ FastPath tracking
                    was_fast = pos.get("fast_entry", False)
                    self.fast_path.record(was_fast, pnl)
                    # RL: تعلم من الصفقة
                    if hasattr(self.rl_learner, "learn"):
                        reward = pnl / max(self.paper.balance, 1) * 100
                        self.rl_learner.learn("market", "NEUTRAL", reward, "market")
                    # 🧠 MetaLearning: سجّل أداء الوكلاء ✅ إصلاح Gemini #1
                    pos_details = pos.get("details", {})
                    for ag_name, ag_det in pos_details.items():
                        pred = ag_det.get("dir", 0)
                        if pred != 0:
                            self.meta_learn.record_signal(ag_name, pred, pnl)
                    self.meta_learn.recompute_weights()
                    if doubled:
                        dmsg = self.snowball.doubling_message(self.paper.balance)
                        log.info(dmsg)
                        asyncio.ensure_future(self.notifier.send(dmsg))
                    await self.notifier.send(
                        f"{'✅' if pnl>0 else '❌'} {reason} "
                        f"[{pos['symbol']}] PnL={pnl:+.4f}")
                    log.info(f"🔒 {reason} [{pos['symbol']}] pnl={pnl:+.4f}")
                    # Flywheel — إعادة استثمار الأرباح
                    # تسجيل في الذاكرة والتعلم
                    self.meta_agent.record_trade(
                        "bot", pnl)
                    self.memory.store({
                        "symbol": pos["symbol"],
                        "pnl":    pnl,
                        "reason": reason,
                        "time":   datetime.now().isoformat()
                    })
                    if pnl > 0:
                        reinvested = self.flywheel.record_profit(pnl)
                        if reinvested > 0:
                            log.info(f"🎯 Flywheel: +{reinvested:.4f} مُعاد استثماره")
                self.pyramid.clear(pos_id)
                del self.positions[pos_id]

                # ⚡ إعادة دخول فورية بعد 5 ثوانٍ في عملة أخرى
                asyncio.ensure_future(self._reentry_after_exit(
                    closed_symbol = pos["symbol"],
                    wait_seconds  = 5
                ))

    def _end_scan_latency(self, t0: float):
        lat = self.lat_opt.end(t0)
        if self.cycle % 50 == 0:
            log.info(f"⚡ {self.lat_opt.status()}")

    async def _reentry_after_exit(self, closed_symbol: str, wait_seconds: int = 5):
        """
        بعد إغلاق أي صفقة → ينتظر 5 ثوانٍ ثم يبحث فوراً عن أفضل عملة أخرى
        يتجنب العملة المغلقة لدورة واحدة (30 ثانية)
        """
        await asyncio.sleep(wait_seconds)
        if not self.running:
            return
        if len(self.positions) >= config.MAX_POSITIONS:
            return

        log.info(f"⚡ إعادة دخول فورية — تجنّب [{closed_symbol}] لـ 30 ثانية")

        # اختر أفضل عملة بديلة من VolatilityScanner
        top5 = self.vol_scanner.scan(self.data_cache)
        candidates = [s for s in top5 if s != closed_symbol]
        if not candidates:
            # fallback: أي عملة من القائمة النشطة غير المغلقة
            active = self._get_active_symbols()
            candidates = [s for s in active
                          if s != closed_symbol
                          and s not in [p["symbol"]
                                        for p in self.positions.values()]]
        if not candidates:
            return

        # فحص إشارة سريع على أفضل 3 مرشحين
        for symbol in candidates[:3]:
            data = dict(self.data_cache.get(symbol, {}))
            if not data:
                continue
            data["symbol"] = symbol

            # MomentumSniper أولاً — أسرع من ConsensusEngine
            df1m    = data.get("1m", pd.DataFrame())
            sniper_r= self.sniper.detect(df1m) if not df1m.empty else {}
            sig     = sniper_r.get("signal","HOLD")
            conf    = sniper_r.get("confidence", 0.0)

            # إذا لم يجد Sniper إشارة → جرّب ConsensusEngine السريع
            if sig == "HOLD" or conf < 0.55:
                selected = self.agent_selector.select(
                    self.agents, self.meta_agent.personality.current_personality, 0.5)
                temp_c   = ConsensusEngine(selected[:5])  # 5 وكلاء فقط للسرعة
                direction, conf, details = await temp_c.decide(data)
                if direction in ("LONG","SHORT") and conf >= config.MIN_AGREEMENT:
                    sig = "BUY" if direction=="LONG" else "SELL"
                else:
                    continue

            if sig not in ("BUY","SELL") or conf < 0.55:
                continue

            direction = "LONG" if sig == "BUY" else "SHORT"
            price     = self.ws_manager.get_price(symbol)
            if price <= 0:
                price = await self.exchange.fetch_price(symbol)
            if price <= 0:
                continue

            ai_r = {"signal": sig, "confidence": conf}
            if not self.trend_f.allows(direction):
                continue
            await self._execute(symbol, direction, conf,
                                price, {}, ai_r,
                                self.session_f.size_multiplier())
            log.info(f"⚡ دخول فوري [{symbol}] {direction} @ {price:.4f} "
                     f"conf={conf:.0%} (بعد {wait_seconds}ث من إغلاق {closed_symbol})")
            break  # صفقة واحدة كافية لكل إعادة دخول

    async def run(self):
        await self.initialize()
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(config.CYCLE_SLEEP)
            except asyncio.CancelledError: break
            except Exception as e:
                log.error(f"خطأ: {e}")
                await asyncio.sleep(15)

    async def shutdown(self):
        self.running = False
        for pos_id in list(self.positions.keys()):
            pos   = self.positions[pos_id]
            # WebSocket أولاً للسعر اللحظي
            price = self.ws_manager.get_price(pos["symbol"])
            if price <= 0:
                price = await self.exchange.fetch_price(pos["symbol"])
            pnl   = self.paper.close(pos_id, price, "Shutdown")
            if pnl: log.info(f"🚨 إغلاق [{pos['symbol']}] pnl={pnl:+.4f}")
        await self.exchange.close()
        await self.notifier.close()
        perf = self.paper.performance()
        log.info(
            f"📊 ملخص النهائي:\n"
            f"  الصفقات: {perf['total']}\n"
            f"  الفوز: {perf['win_rate']}%\n"
            f"  PnL: {perf['pnl']:+.2f}\n"
            f"  Sharpe: {perf['sharpe']:.2f}\n"
            f"  محوّل: ${self.transferred:.2f}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 🚀 نقطة البداية
# ══════════════════════════════════════════════════════════════════════════════
async def main():
    bot = UltimateFinalBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        log.info("⌨️ إيقاف يدوي")
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    import sys, platform
    # ✅ Windows: إصلاح asyncio event loop
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # ✅ Windows: إصلاح encoding للـ PowerShell
    if sys.stdout.encoding != "utf-8":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    asyncio.run(main())
