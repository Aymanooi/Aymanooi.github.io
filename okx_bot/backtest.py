"""
backtest.py — محرّك اختبار رجعي (Backtesting) مثل Freqtrade
─────────────────────────────────────────────────────────────────────────────
يختبر استراتيجية analyze() نفسها على بيانات تاريخية حقيقية من OKX، ويحاكي
بدقّة نفس منطق البوت الحيّ:
  • دخول عند الإشارة (نفس العتبة THRESHOLD في strategy.py)
  • SL = 1.5×ATR  /  TP = 4.5×ATR  (RR = 3:1)
  • وقف متحرّك متدرّج (_trail_floor) ونفس قاطع الدائرة −50%
  • نفس الرافعة من config.py

يطبع تقريراً: عدد الصفقات، معدّل الفوز، عامل الربح، أقصى تراجع، ومنحنى
رأس المال التقريبي — حتى تعرف إن كانت الإعدادات تربح فعلاً قبل المخاطرة بالمال.

التشغيل:
    python okx_bot/backtest.py              # 30 عملة، 300 شمعة 15m
    python okx_bot/backtest.py 50 300       # 50 عملة، 300 شمعة
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from strategy import analyze
import config as cfg

# نفس ثوابت المدير الحيّ في run_once.py
HARD_STOP = -0.50   # قاطع دائرة عند −50% هامش
HARD_TAKE = 2.00    # سقف أمان +200%
WARMUP    = 60      # شمعات تهيئة قبل أول إشارة


def _trail_floor(peak):
    """نسخة طبق الأصل من run_once._trail_floor — حتى يطابق الباكتيست الواقع."""
    if peak < 0.25:
        return None
    if peak < 0.50:
        return peak - 0.15
    if peak < 1.00:
        return peak * 0.70
    if peak < 2.00:
        return peak * 0.80
    return peak * 0.85


def simulate(chron15, chron1h, leverage):
    """
    يحاكي التداول على سلسلة شموع واحدة (مرتّبة من الأقدم للأحدث).
    chron15/chron1h: قوائم شموع OKX [ts, o, h, l, c, vol, ...] أقدم أولاً.
    يُرجع قائمة بنتائج الصفقات: كل عنصر = العائد على الهامش (٪، يشمل الرافعة).
    شبكة الأمان: لا توجد عمليّات شبكة هنا — دالة نقيّة قابلة للاختبار.
    """
    returns = []
    pos = None   # {'side','entry','sl','tp','peak'}

    for i in range(WARMUP, len(chron15)):
        bar = chron15[i]
        ts   = int(bar[0])
        high = float(bar[2])
        low  = float(bar[3])
        close = float(bar[4])

        # ── إدارة مركز مفتوح بهذه الشمعة ──────────────────────────────
        if pos:
            entry = pos["entry"]
            if pos["side"] == "buy":
                ratio_fav = (high / entry - 1) * leverage   # أفضل نقطة
                ratio_cls = (close / entry - 1) * leverage
                hit_sl = low <= pos["sl"]
                hit_tp = high >= pos["tp"]
                sl_ret = (pos["sl"] / entry - 1) * leverage
                tp_ret = (pos["tp"] / entry - 1) * leverage
            else:
                ratio_fav = (1 - low / entry) * leverage
                ratio_cls = (1 - close / entry) * leverage
                hit_sl = high >= pos["sl"]
                hit_tp = low <= pos["tp"]
                sl_ret = (1 - pos["sl"] / entry) * leverage
                tp_ret = (1 - pos["tp"] / entry) * leverage

            pos["peak"] = max(pos["peak"], ratio_fav)

            exit_ret = None
            # أولويّة محافِظة: SL أولاً (لا نعرف ترتيب high/low داخل الشمعة)
            if hit_sl:
                exit_ret = sl_ret
            elif hit_tp:
                exit_ret = tp_ret
            elif ratio_cls <= HARD_STOP:
                exit_ret = ratio_cls
            elif ratio_cls >= HARD_TAKE:
                exit_ret = ratio_cls
            else:
                floor = _trail_floor(pos["peak"])
                if floor is not None and ratio_cls <= floor:
                    exit_ret = ratio_cls

            if exit_ret is not None:
                returns.append(max(exit_ret, -1.0))   # لا تخسر أكثر من الهامش
                pos = None

        # ── البحث عن دخول جديد عندما لا يوجد مركز ──────────────────────
        if not pos:
            window15 = list(reversed(chron15[i - WARMUP:i + 1]))   # أحدث أولاً
            h1 = [c for c in chron1h if int(c[0]) <= ts][-60:]
            window1h = list(reversed(h1)) if len(h1) >= 26 else None
            r = analyze(window15, window1h)
            if r["signal"] and r.get("atr", 0) > 0:
                pos = {
                    "side":  r["signal"],
                    "entry": close,
                    "sl":    r["sl_price"],
                    "tp":    r["tp_price"],
                    "peak":  0.0,
                }
    return returns


def report(all_returns, start_equity=10.0, risk_per_trade=1.0):
    """يحسب ويطبع مقاييس الأداء من قائمة عوائد الصفقات (٪ على الهامش)."""
    n = len(all_returns)
    if n == 0:
        print("⚠️  لا توجد صفقات في فترة الاختبار — جرّب عملات أكثر أو عتبة أقل.")
        return

    wins   = [r for r in all_returns if r > 0]
    losses = [r for r in all_returns if r <= 0]
    win_rate = len(wins) / n * 100
    gross_win  = sum(wins)
    gross_loss = -sum(losses)
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    avg = sum(all_returns) / n

    # منحنى رأس مال تقريبي: كل صفقة تخاطر بنسبة risk_per_trade من الرصيد
    equity = start_equity
    peak_eq = start_equity
    max_dd = 0.0
    for r in all_returns:
        equity *= (1 + r * risk_per_trade)
        equity = max(equity, 0.0)
        peak_eq = max(peak_eq, equity)
        if peak_eq > 0:
            max_dd = max(max_dd, (peak_eq - equity) / peak_eq)

    # أطول سلسلة خسائر متتالية
    streak = worst_streak = 0
    for r in all_returns:
        streak = streak + 1 if r <= 0 else 0
        worst_streak = max(worst_streak, streak)

    print("\n" + "═" * 56)
    print("📊  نتائج الاختبار الرجعي (Backtest)")
    print("═" * 56)
    print(f"  عدد الصفقات        : {n}")
    print(f"  فوز / خسارة        : {len(wins)} / {len(losses)}")
    print(f"  معدّل الفوز         : {win_rate:.1f}%   (التعادل عند RR=3:1 هو 25%)")
    print(f"  متوسّط العائد/صفقة  : {avg*100:+.2f}% على الهامش")
    print(f"  عامل الربح (PF)     : {profit_factor:.2f}   (>1 = رابح)")
    print(f"  أطول سلسلة خسائر    : {worst_streak}")
    print(f"  أقصى تراجع (DD)     : {max_dd*100:.1f}%")
    print("─" * 56)
    print(f"  رأس مال تقريبي      : ${start_equity:.2f} → ${equity:.2f}")
    print(f"  (افتراض: كل صفقة تخاطر بـ{risk_per_trade*100:.0f}% من الرصيد — توضيحي)")
    print("═" * 56)
    verdict = "✅ الاستراتيجية رابحة في هذه الفترة" if profit_factor > 1 \
              else "❌ الاستراتيجية خاسرة في هذه الفترة — لا تخاطر بمال حقيقي"
    print(f"  {verdict}")
    print("═" * 56 + "\n")


def main():
    n_symbols = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    n_bars    = int(sys.argv[2]) if len(sys.argv) > 2 else 300

    from okx_client import OKXClient
    # بيانات الشموع عامّة — لا حاجة لمفاتيح حقيقية (لا تشارك مفاتيحك أبداً)
    client = OKXClient("public", "public", "public", is_demo="0")

    print(f"⏳ جلب {n_bars} شمعة لأعلى {n_symbols} عملة من OKX...")
    try:
        pairs = client.get_top_pairs(n_symbols)
    except Exception as e:
        print(f"❌ تعذّر الاتصال بـ OKX: {e}")
        sys.exit(1)

    leverage = cfg.LEVERAGE
    all_returns = []
    tested = 0
    for sym in pairs:
        try:
            raw15 = client.get_candles(sym, bar="15m", limit=n_bars)
            raw1h = client.get_candles(sym, bar="1H", limit=n_bars)
            if len(raw15) < WARMUP + 10:
                continue
            chron15 = list(reversed(raw15))
            chron1h = list(reversed(raw1h))
            rets = simulate(chron15, chron1h, leverage)
            all_returns.extend(rets)
            tested += 1
            if rets:
                print(f"  {sym:<22} {len(rets):>3} صفقة")
        except Exception:
            continue

    print(f"\n✔️ اكتُمل الاختبار على {tested} عملة | رافعة x{leverage} | عتبة {cfg.SIGNAL_THRESHOLD}")
    report(all_returns)


if __name__ == "__main__":
    main()
