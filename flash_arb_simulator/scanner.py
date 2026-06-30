#!/usr/bin/env python3
"""
ماسح شامل: يكتشف عملات سولانا تلقائياً ويفحص كل واحدة بحثاً عن مراجحة.

الفكرة التي طلبها المستخدم: "لا تفحص 12 عملة — افحص كل العملات، لا بد أن
واحدة منها مربحة." هذا المنطق سليم، وهذه الأداة تنفّذه بأمانة كاملة:

  - تجلب أكثر العملات تداولاً على سولانا من Jupiter (المجال الوحيد الذي
    تكفي سيولته لتنفيذ صفقة حقيقية).
  - تفحص لكل عملة حلقة:  base → SOL → TOKEN → base
  - تحسب صافي الربح بعد رسوم القرض الوميضي ورسوم الشبكة.
  - تعرض أي فرصة موجبة، وملخّصاً إحصائياً صادقاً.

⚠️  وضع المحاكاة فقط: قراءة أسعار، لا تنفيذ، لا مفاتيح خاصة.

ملاحظة صادقة: "كل عملة على سولانا" حرفياً = عشرات الآلاف، أغلبها ميتة بسيولة
صفر (لا يمكن تمرير دولار واحد خلالها). لذلك نفحص "الكون القابل للتداول" —
وهو بالضبط المكان الذي قد توجد فيه فرصة قابلة للتنفيذ فعلاً.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone

from config import MINTS, DECIMALS, Settings
from detector import to_atomic, from_atomic
from jupiter import JupiterClient, JupiterError, NoRouteError
from logger import CsvLogger


TOKENS_URL = "https://lite-api.jup.ag/tokens/v2/toptraded/24h?limit={limit}"


def fetch_tokens(limit: int, timeout: int = 30) -> list[dict]:
    """يجلب أكثر العملات تداولاً خلال 24 ساعة (الأعلى سيولة)."""
    url = TOKENS_URL.format(limit=min(limit, 100))
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "flash-arb-simulator/1.0 (educational; read-only)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = []
    for t in data:
        sym = t.get("symbol") or t.get("id", "")[:6]
        out.append({"symbol": sym, "mint": t["id"],
                    "decimals": int(t["decimals"]),
                    "holders": t.get("holderCount", 0)})
    return out


def evaluate_token(client: JupiterClient, settings: Settings, token: dict,
                   sol_price_in_base: float) -> dict | None:
    """
    يفحص حلقة base → SOL → TOKEN → base لعملة واحدة.
    يعيد قاموس النتيجة، أو None إن تعذّر (لا مسار / سيولة).
    """
    base = settings.base_token
    base_mint = MINTS[base]
    base_dec = DECIMALS[base]
    sol_mint = MINTS["SOL"]
    tok_mint = token["mint"]
    tok_dec = token["decimals"]

    start_atomic = int(round(settings.base_amount * (10 ** base_dec)))

    try:
        # القفزة 1: base -> SOL
        q1 = client.quote(base_mint, sol_mint, start_atomic)
        sol_amt = int(q1["outAmount"])
        # القفزة 2: SOL -> TOKEN
        q2 = client.quote(sol_mint, tok_mint, sol_amt)
        tok_amt = int(q2["outAmount"])
        # القفزة 3: TOKEN -> base
        q3 = client.quote(tok_mint, base_mint, tok_amt)
        end_atomic = int(q3["outAmount"])
    except NoRouteError:
        return None
    except JupiterError:
        return None

    start_amount = start_atomic / (10 ** base_dec)
    end_amount = end_atomic / (10 ** base_dec)
    gross = end_amount - start_amount

    flash_fee = start_amount * (settings.fees.flash_loan_fee_bps / 10_000.0)
    f = settings.fees
    chain_fees = ((f.base_tx_fee_sol + f.priority_fee_sol + f.jito_tip_sol)
                  * sol_price_in_base)
    total_fees = flash_fee + chain_fees
    net = gross - total_fees

    max_impact = max(
        abs(float(q1.get("priceImpactPct") or 0)),
        abs(float(q2.get("priceImpactPct") or 0)),
        abs(float(q3.get("priceImpactPct") or 0)),
    ) * 100.0

    return {
        "symbol": token["symbol"],
        "cycle": [base, "SOL", token["symbol"], base],
        "start_amount": start_amount,
        "end_amount": end_amount,
        "gross_profit": gross,
        "total_fees": total_fees,
        "net_profit": net,
        "net_profit_pct": (net / start_amount * 100.0) if start_amount else 0,
        "max_price_impact_pct": max_impact,
    }


def estimate_sol_price(client: JupiterClient, settings: Settings) -> float:
    base = settings.base_token
    if base == "SOL":
        return 1.0
    q = client.quote(MINTS["SOL"], MINTS[base], to_atomic(1.0, "SOL"))
    return from_atomic(int(q["outAmount"]), base)


def main() -> int:
    p = argparse.ArgumentParser(
        description="ماسح شامل لعملات سولانا (محاكاة فقط — لا تنفيذ)")
    p.add_argument("--limit", type=int, default=50,
                   help="عدد العملات المراد فحصها (الأعلى تداولاً، حد 100)")
    p.add_argument("--amount", type=float, default=1000.0,
                   help="مبلغ البدء بالعملة الأساسية")
    p.add_argument("--base", default="USDC", help="العملة الأساسية")
    p.add_argument("--flash-fee-bps", type=float, default=30.0,
                   help="رسوم القرض الوميضي بنقاط الأساس")
    p.add_argument("--delay", type=float, default=0.25,
                   help="تأخير بين الطلبات (ثوانٍ) لاحترام حدود الواجهة")
    p.add_argument("--csv", default=None, help="مسار CSV لتسجيل كل النتائج")
    p.add_argument("--top", type=int, default=15,
                   help="عدد أفضل النتائج المعروضة")
    args = p.parse_args()

    settings = Settings()
    settings.base_token = args.base.upper()
    settings.base_amount = args.amount
    settings.fees.flash_loan_fee_bps = args.flash_fee_bps
    base = settings.base_token

    client = JupiterClient(settings.jupiter_base_url, settings.slippage_bps)
    csv_logger = CsvLogger(args.csv) if args.csv else None

    print("=" * 72)
    print("🔭 ماسح شامل لعملات سولانا — وضع المحاكاة فقط")
    print("=" * 72)

    # تأكّد أن العملة الأساسية وSOL ضمن الخريطة
    if base not in MINTS or "SOL" not in MINTS:
        print("❌ العملة الأساسية أو SOL غير معرّفة في config.MINTS")
        return 1

    try:
        sol_price = estimate_sol_price(client, settings)
    except JupiterError as e:
        print(f"❌ تعذّر تقدير سعر SOL: {e}")
        return 1

    print(f"💰 الأساس: {base} | مبلغ البدء: {args.amount:,.2f} | "
          f"رسوم القرض: {args.flash_fee_bps} bps | SOL≈{sol_price:,.2f} {base}")

    try:
        tokens = fetch_tokens(args.limit)
    except Exception as e:
        print(f"❌ تعذّر جلب قائمة العملات: {e}")
        return 1

    # سجّل عناوين العملات المكتشفة مؤقتاً كي تستطيع quote العمل
    for t in tokens:
        MINTS.setdefault(t["symbol"], t["mint"])
        DECIMALS.setdefault(t["symbol"], t["decimals"])

    print(f"🔍 سيتم فحص {len(tokens)} عملة (الأعلى تداولاً خلال 24 ساعة)\n")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []
    skipped = 0
    for i, tok in enumerate(tokens, 1):
        if tok["mint"] in (MINTS["SOL"], MINTS[base]):
            continue
        res = evaluate_token(client, settings, tok, sol_price)
        print(f"\r   تقدّم: {i}/{len(tokens)}  "
              f"(فرص حتى الآن: {sum(1 for r in results if r['net_profit']>0)})",
              end="", flush=True)
        if res is None:
            skipped += 1
        else:
            results.append(res)
            if csv_logger:
                # غلاف بسيط ليتوافق مع CsvLogger.log
                class _R:
                    pass
                r = _R()
                for k, v in res.items():
                    setattr(r, k, v)
                csv_logger.log(r, base, sol_price,
                               settings.fees.flash_loan_fee_bps, ts=ts)
        time.sleep(args.delay)
    print()  # سطر جديد بعد شريط التقدّم

    results.sort(key=lambda r: r["net_profit"], reverse=True)
    opportunities = [r for r in results if r["net_profit"] > 0]

    print("\n" + "=" * 72)
    print(f"📊 النتائج: فُحصت {len(results)} حلقة | "
          f"تُخطّيت {skipped} (لا سيولة كافية)")
    print("=" * 72)

    print(f"\n🏆 أفضل {min(args.top, len(results))} حلقة (الأقرب للربح):")
    for r in results[:args.top]:
        flag = "✅" if r["net_profit"] > 0 else "❌"
        sign = "+" if r["net_profit"] >= 0 else ""
        print(f"  {flag} {' → '.join(r['cycle']):<28} "
              f"صافي: {sign}{r['net_profit']:>12,.4f} {base} "
              f"({sign}{r['net_profit_pct']:.4f}%) "
              f"| تأثير: {r['max_price_impact_pct']:.3f}%")

    print("\n" + "-" * 72)
    if opportunities:
        print(f"🎯 وُجدت {len(opportunities)} فرصة موجبة (نظرياً، قبل المنافسة):")
        for r in opportunities:
            print(f"   ✅ {' → '.join(r['cycle'])}: "
                  f"+{r['net_profit']:,.4f} {base}")
        print("\n⚠️  تنبيه صادق: هذه الفرص — إن وُجدت — تعيش أجزاء من الثانية،")
        print("   وتلتقطها بوتات احترافية (Jito + RPC خاص) قبلك. ظهورها هنا")
        print("   لا يعني أنك تستطيع تنفيذها فعلياً.")
    else:
        print(f"😐 صفر فرص مربحة من بين {len(results)} عملة فُحصت.")
        print("   هذا بالضبط جواب سؤالك: حتى بفحص الكون القابل للتداول كله،")
        print("   السوق فعّال ولا يترك ربحاً مجانياً للأفراد.")
    print("-" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
