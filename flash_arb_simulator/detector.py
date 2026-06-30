"""
المنطق الأساسي لكشف المراجحة الثلاثية (محاكاة فقط).

الفكرة:
  نبدأ بمبلغ X من العملة الأساسية، نمرّ عبر حلقة من التبديلات
  (مثل USDC -> SOL -> BONK -> USDC) باستخدام أفضل مسار من Jupiter لكل قفزة،
  ثم نقارن المبلغ النهائي بالمبلغ الابتدائي بعد خصم كل الرسوم.

  إن كان الناتج النهائي > المبلغ الابتدائي + الرسوم => فرصة مراجحة نظرية.

لا تنفيذ فعلي: نقرأ الأسعار فقط ونحسب الأرقام.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import MINTS, DECIMALS, Settings
from jupiter import JupiterClient


def to_atomic(amount: float, symbol: str) -> int:
    return int(round(amount * (10 ** DECIMALS[symbol])))


def from_atomic(amount: int, symbol: str) -> float:
    return amount / (10 ** DECIMALS[symbol])


@dataclass
class Leg:
    src: str
    dst: str
    in_amount: int
    out_amount: int
    price_impact_pct: float


@dataclass
class CycleResult:
    cycle: list
    legs: list
    start_amount: float       # بالعملة الأساسية (مقروء)
    end_amount: float         # بالعملة الأساسية (مقروء)
    gross_profit: float       # قبل الرسوم
    total_fees: float         # بالعملة الأساسية
    net_profit: float         # بعد كل الرسوم
    net_profit_pct: float
    max_price_impact_pct: float

    @property
    def is_opportunity(self) -> bool:
        return self.net_profit > 0


def _fees_in_base(settings: Settings, sol_price_in_base: float) -> tuple[float, float]:
    """
    يعيد (رسوم_القرض_الوميضي, رسوم_السلسلة) بالعملة الأساسية.

    رسوم القرض الوميضي تُحسب لاحقاً كنسبة من المبلغ المقترض؛ هنا نعيد فقط
    رسوم السلسلة الثابتة (tx + priority + jito) محوّلة إلى العملة الأساسية.
    """
    f = settings.fees
    sol_fees = f.base_tx_fee_sol + f.priority_fee_sol + f.jito_tip_sol
    chain_fees_base = sol_fees * sol_price_in_base
    return chain_fees_base


def evaluate_cycle(client: JupiterClient, settings: Settings,
                   cycle: list, sol_price_in_base: float) -> CycleResult:
    """
    يقيّم حلقة مراجحة واحدة ويعيد النتيجة المفصّلة.
    """
    assert cycle[0] == cycle[-1] == settings.base_token, \
        "يجب أن تبدأ الحلقة وتنتهي بالعملة الأساسية"

    base = settings.base_token
    current_symbol = base
    current_atomic = to_atomic(settings.base_amount, base)
    start_amount = settings.base_amount

    legs: list[Leg] = []
    max_impact = 0.0

    for nxt in cycle[1:]:
        q = client.quote(MINTS[current_symbol], MINTS[nxt], current_atomic)
        out_atomic = int(q["outAmount"])
        impact = abs(float(q.get("priceImpactPct") or 0.0)) * 100.0
        max_impact = max(max_impact, impact)

        legs.append(Leg(
            src=current_symbol, dst=nxt,
            in_amount=current_atomic, out_amount=out_atomic,
            price_impact_pct=impact,
        ))
        current_symbol = nxt
        current_atomic = out_atomic

    end_amount = from_atomic(current_atomic, base)
    gross_profit = end_amount - start_amount

    # رسوم القرض الوميضي: نسبة من المبلغ المقترض (= المبلغ الابتدائي)
    flash_fee = start_amount * (settings.fees.flash_loan_fee_bps / 10_000.0)
    chain_fees = _fees_in_base(settings, sol_price_in_base)
    total_fees = flash_fee + chain_fees

    net_profit = gross_profit - total_fees
    net_profit_pct = (net_profit / start_amount) * 100.0 if start_amount else 0.0

    return CycleResult(
        cycle=cycle,
        legs=legs,
        start_amount=start_amount,
        end_amount=end_amount,
        gross_profit=gross_profit,
        total_fees=total_fees,
        net_profit=net_profit,
        net_profit_pct=net_profit_pct,
        max_price_impact_pct=max_impact,
    )


def estimate_sol_price_in_base(client: JupiterClient, settings: Settings) -> float:
    """
    يقدّر سعر SOL مقوّماً بالعملة الأساسية عبر اقتباس 1 SOL -> base.
    يُستخدم لتحويل الرسوم المقوّمة بـ SOL إلى العملة الأساسية.
    """
    base = settings.base_token
    if base == "SOL":
        return 1.0
    one_sol = to_atomic(1.0, "SOL")
    q = client.quote(MINTS["SOL"], MINTS[base], one_sol)
    return from_atomic(int(q["outAmount"]), base)
