#!/usr/bin/env python3
"""
كاشف مراجحة القروض الوميضية على سولانا — وضع المحاكاة فقط.

⚠️  هذه الأداة للأغراض التعليمية والبحثية فقط:
    - تقرأ الأسعار الحقيقية من Jupiter (نقطة /quote).
    - تحسب صافي الربحية بعد كل الرسوم.
    - لا تبني ولا توقّع ولا ترسل أي معاملة.
    - لا تتعامل مع أي مفتاح خاص.

الاستخدام:
    python3 main.py
    python3 main.py --amount 50000 --base USDC
    python3 main.py --watch 15          # تكرار كل 15 ثانية
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from config import Settings
from detector import (JupiterClient, evaluate_cycle,
                      estimate_sol_price_in_base)
from jupiter import JupiterError
from logger import CsvLogger


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="كاشف مراجحة سولانا (محاكاة فقط — لا تنفيذ فعلي)")
    p.add_argument("--base", default=None,
                   help="العملة الأساسية (افتراضي من الإعدادات)")
    p.add_argument("--amount", type=float, default=None,
                   help="مبلغ البدء بالعملة الأساسية")
    p.add_argument("--flash-fee-bps", type=float, default=None,
                   help="رسوم القرض الوميضي بنقاط الأساس")
    p.add_argument("--watch", type=int, default=0,
                   help="التكرار كل N ثانية (0 = مرة واحدة)")
    p.add_argument("--show-all", action="store_true",
                   help="إظهار كل الحلقات حتى الخاسرة")
    p.add_argument("--csv", default=None,
                   help="مسار ملف CSV لتسجيل كل النتائج (اختياري)")
    return p.parse_args()


def build_settings(args: argparse.Namespace) -> Settings:
    s = Settings()
    if args.base:
        s.base_token = args.base.upper()
    if args.amount is not None:
        s.base_amount = args.amount
    if args.flash_fee_bps is not None:
        s.fees.flash_loan_fee_bps = args.flash_fee_bps
    return s


def fmt(x: float, nd: int = 4) -> str:
    return f"{x:,.{nd}f}"


def run_once(client: JupiterClient, settings: Settings, show_all: bool,
             csv_logger: CsvLogger | None = None) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = settings.base_token

    try:
        sol_price = estimate_sol_price_in_base(client, settings)
    except JupiterError as e:
        print(f"[{ts}] تعذّر تقدير سعر SOL: {e}", file=sys.stderr)
        sol_price = settings.sol_price_usd

    settings.sol_price_usd = sol_price

    print("=" * 70)
    print(f"⏱  {ts}")
    print(f"💰 العملة الأساسية: {base} | مبلغ البدء: {fmt(settings.base_amount, 2)}")
    print(f"📈 سعر SOL ≈ {fmt(sol_price, 2)} {base} | "
          f"رسوم القرض الوميضي: {settings.fees.flash_loan_fee_bps} bps")
    print("=" * 70)

    results = []
    for cycle in settings.cycles:
        label = " → ".join(cycle)
        try:
            res = evaluate_cycle(client, settings, cycle, sol_price)
            results.append(res)
            if csv_logger is not None:
                csv_logger.log(res, base, sol_price,
                               settings.fees.flash_loan_fee_bps, ts=iso_ts)
        except (JupiterError, AssertionError) as e:
            print(f"  ⚠️  {label}: خطأ — {e}")

    # رتّب من الأفضل ربحاً
    results.sort(key=lambda r: r.net_profit, reverse=True)

    opportunities = 0
    for r in results:
        label = " → ".join(r.cycle)
        is_opp = r.net_profit > settings.min_net_profit
        if is_opp:
            opportunities += 1
        if not is_opp and not show_all:
            continue

        flag = "✅ فرصة" if is_opp else "❌ خاسرة"
        sign = "+" if r.net_profit >= 0 else ""
        print(f"\n{flag}  {label}")
        print(f"   البدء: {fmt(r.start_amount, 2)} {base}  →  "
              f"النهاية: {fmt(r.end_amount, 2)} {base}")
        print(f"   ربح إجمالي: {fmt(r.gross_profit)} {base} | "
              f"رسوم: {fmt(r.total_fees)} {base}")
        print(f"   صافي الربح: {sign}{fmt(r.net_profit)} {base} "
              f"({sign}{fmt(r.net_profit_pct, 4)}%) | "
              f"أقصى تأثير سعري: {fmt(r.max_price_impact_pct, 4)}%")

    print("\n" + "-" * 70)
    if opportunities:
        print(f"🎯 عدد الفرص المربحة نظرياً: {opportunities} من {len(results)}")
    else:
        print(f"😐 لا فرص مربحة الآن (فحصنا {len(results)} حلقة). "
              f"هذا طبيعي — السوق فعّال والمنافسة شديدة.")
    print("-" * 70)


def main() -> int:
    args = parse_args()
    settings = build_settings(args)
    client = JupiterClient(settings.jupiter_base_url, settings.slippage_bps)
    csv_logger = CsvLogger(args.csv) if args.csv else None
    if csv_logger:
        print(f"📝 تسجيل النتائج في: {args.csv}")

    if args.watch <= 0:
        run_once(client, settings, args.show_all, csv_logger)
        return 0

    print(f"🔁 وضع المراقبة: كل {args.watch} ثانية (Ctrl+C للإيقاف)")
    try:
        while True:
            run_once(client, settings, args.show_all, csv_logger)
            time.sleep(args.watch)
    except KeyboardInterrupt:
        print("\n⏹  تم الإيقاف.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
