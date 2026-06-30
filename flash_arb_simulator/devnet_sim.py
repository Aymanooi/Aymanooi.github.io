#!/usr/bin/env python3
"""
محاكاة تنفيذ قرض وميضي على نمط devnet — بأموال وهمية ومحلية بالكامل.

⚠️  ماذا تفعل هذه الأداة:
    - تبني تسلسل التعليمات الفعلي لقرض وميضي:
        flashBorrow → swap₁ → swap₂ → … → flashRepay
    - تطبّقها على "دفتر أستاذ" وهمي محلي وتفرض قاعدة الذرّية (atomicity):
      إن لم يكفِ المبلغ النهائي لسداد القرض + الرسوم، تُلغى المعاملة بالكامل
      (rollback) — تماماً كما يحدث على سولانا الحقيقية.
    - تجلب نسب التحويل الحقيقية من Jupiter لجعل المحاكاة واقعية.
    - (اختياري) تتصل بـ devnet RPC للتحقق من الاتصال وقراءة رقم الـ slot.

❌  ماذا لا تفعل:
    - لا ترسل أي معاملة حقيقية إلى أي شبكة.
    - لا تستخدم أي مفتاح خاص أو محفظة.
    - لا أموال حقيقية إطلاقاً — كل الأرصدة وهمية.

الهدف: فهم *كيف* تنجح أو تفشل معاملة القرض الوميضي ذرّياً قبل أي تنفيذ حقيقي.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from dataclasses import dataclass, field

from config import MINTS, DECIMALS, Settings
from detector import to_atomic, from_atomic
from jupiter import JupiterClient, JupiterError


DEVNET_RPC = "https://api.devnet.solana.com"


# --------------------------------------------------------------------------- #
# نموذج التعليمات والمعاملة الذرّية
# --------------------------------------------------------------------------- #

@dataclass
class Instruction:
    kind: str            # "flash_borrow" | "swap" | "flash_repay"
    description: str
    apply_fn: object     # دالة تعدّل دفتر الأستاذ الوهمي


@dataclass
class Ledger:
    """دفتر أستاذ وهمي: رصيد كل عملة (بوحدات ذرّية)."""
    balances: dict = field(default_factory=dict)
    debt: int = 0           # المبلغ المستحق سداده للقرض الوميضي (ذرّي)
    debt_symbol: str = ""

    def credit(self, symbol: str, amount: int) -> None:
        self.balances[symbol] = self.balances.get(symbol, 0) + amount

    def debit(self, symbol: str, amount: int) -> None:
        bal = self.balances.get(symbol, 0)
        if amount > bal:
            raise ValueError(
                f"رصيد غير كافٍ من {symbol}: مطلوب {amount} متاح {bal}")
        self.balances[symbol] = bal - amount

    def snapshot(self) -> dict:
        return {"balances": dict(self.balances),
                "debt": self.debt, "debt_symbol": self.debt_symbol}

    def restore(self, snap: dict) -> None:
        self.balances = dict(snap["balances"])
        self.debt = snap["debt"]
        self.debt_symbol = snap["debt_symbol"]


class FlashTxFailed(Exception):
    """تُرفع عند انتهاك قاعدة الذرّية — تؤدي إلى rollback كامل."""


def build_flash_loan_tx(client: JupiterClient, settings: Settings,
                        cycle: list) -> tuple[list, dict]:
    """
    يبني تسلسل تعليمات القرض الوميضي للحلقة، مع جلب نسب Jupiter الحقيقية.
    يعيد (قائمة التعليمات، بيانات وصفية).
    """
    base = settings.base_token
    assert cycle[0] == cycle[-1] == base
    borrow_atomic = to_atomic(settings.base_amount, base)
    flash_fee = int(borrow_atomic * settings.fees.flash_loan_fee_bps / 10_000)

    instructions: list[Instruction] = []

    # 1) تعليمة الاقتراض
    def _borrow(ledger: Ledger):
        ledger.credit(base, borrow_atomic)
        ledger.debt = borrow_atomic + flash_fee
        ledger.debt_symbol = base
    instructions.append(Instruction(
        "flash_borrow",
        f"اقتراض {from_atomic(borrow_atomic, base):,.2f} {base} "
        f"(رسوم {from_atomic(flash_fee, base):,.4f} {base})",
        _borrow))

    # 2) تعليمات التبديل — نجلب النِسَب الحقيقية الآن لبناء معاملة محدّدة
    current_symbol = base
    current_amount = borrow_atomic
    legs_meta = []
    for nxt in cycle[1:]:
        q = client.quote(MINTS[current_symbol], MINTS[nxt], current_amount)
        out_amount = int(q["outAmount"])
        legs_meta.append({"src": current_symbol, "dst": nxt,
                          "in": current_amount, "out": out_amount})

        src, dst, in_amt, out_amt = current_symbol, nxt, current_amount, out_amount

        def _swap(ledger: Ledger, src=src, dst=dst, in_amt=in_amt, out_amt=out_amt):
            ledger.debit(src, in_amt)
            ledger.credit(dst, out_amt)
        instructions.append(Instruction(
            "swap",
            f"تبديل {from_atomic(in_amt, src):,.4f} {src} → "
            f"{from_atomic(out_amt, dst):,.4f} {dst}",
            _swap))

        current_symbol = nxt
        current_amount = out_amount

    # 3) تعليمة السداد — تفرض الذرّية
    def _repay(ledger: Ledger):
        needed = ledger.debt
        have = ledger.balances.get(ledger.debt_symbol, 0)
        if have < needed:
            raise FlashTxFailed(
                f"السداد فشل: مطلوب {from_atomic(needed, base):,.4f} {base} "
                f"متاح {from_atomic(have, base):,.4f} {base} "
                f"(عجز {from_atomic(needed - have, base):,.4f} {base})")
        ledger.debit(ledger.debt_symbol, needed)
        ledger.debt = 0
    instructions.append(Instruction(
        "flash_repay",
        f"سداد {from_atomic(borrow_atomic + flash_fee, base):,.4f} {base}",
        _repay))

    meta = {"borrow_atomic": borrow_atomic, "flash_fee": flash_fee,
            "legs": legs_meta, "final_amount": current_amount}
    return instructions, meta


def simulate_tx(instructions: list, base: str) -> tuple[bool, str, Ledger]:
    """
    ينفّذ التعليمات ذرّياً على دفتر أستاذ وهمي.
    إن فشلت أي تعليمة، يُعاد الدفتر لحالته الأولى (rollback) كما في سولانا.
    """
    ledger = Ledger()
    snapshot = ledger.snapshot()
    try:
        for ins in instructions:
            ins.apply_fn(ledger)
        return True, "نجحت المعاملة ذرّياً ✅", ledger
    except (FlashTxFailed, ValueError) as e:
        ledger.restore(snapshot)   # rollback كامل
        return False, f"أُلغيت المعاملة بالكامل (rollback) ⛔ — {e}", ledger


# --------------------------------------------------------------------------- #
# فحص اتصال devnet (قراءة فقط — اختياري)
# --------------------------------------------------------------------------- #

def devnet_health(timeout: int = 15) -> tuple[bool, str]:
    """يتحقق من اتصال devnet ويقرأ رقم الـ slot الحالي (RPC عام، قراءة فقط)."""
    def _rpc(method: str, params=None):
        payload = json.dumps({"jsonrpc": "2.0", "id": 1,
                              "method": method, "params": params or []}).encode()
        req = urllib.request.Request(
            DEVNET_RPC, data=payload,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    try:
        health = _rpc("getHealth").get("result")
        slot = _rpc("getSlot").get("result")
        return True, f"devnet متصل (health={health}, slot={slot})"
    except Exception as e:
        return False, f"تعذّر الاتصال بـ devnet: {e}"


# --------------------------------------------------------------------------- #
# واجهة سطر الأوامر
# --------------------------------------------------------------------------- #

def main() -> int:
    p = argparse.ArgumentParser(
        description="محاكاة تنفيذ قرض وميضي (نمط devnet، أموال وهمية، بلا تنفيذ حقيقي)")
    p.add_argument("--amount", type=float, default=10_000.0,
                   help="مبلغ الاقتراض بالعملة الأساسية")
    p.add_argument("--base", default="USDC", help="العملة الأساسية")
    p.add_argument("--flash-fee-bps", type=float, default=30.0,
                   help="رسوم القرض الوميضي بنقاط الأساس")
    p.add_argument("--cycle", nargs="+", default=None,
                   help="حلقة مخصّصة، مثل: USDC SOL BONK USDC")
    p.add_argument("--check-devnet", action="store_true",
                   help="فحص اتصال devnet RPC (قراءة فقط)")
    args = p.parse_args()

    settings = Settings()
    settings.base_token = args.base.upper()
    settings.base_amount = args.amount
    settings.fees.flash_loan_fee_bps = args.flash_fee_bps

    base = settings.base_token
    cycle = args.cycle or [base, "SOL", "BONK", base]
    cycle = [c.upper() for c in cycle]

    print("=" * 70)
    print("🧪 محاكاة تنفيذ قرض وميضي — أموال وهمية، بلا تنفيذ حقيقي")
    print("=" * 70)

    if args.check_devnet:
        ok, msg = devnet_health()
        print(f"🌐 {msg}\n")

    client = JupiterClient(settings.jupiter_base_url, settings.slippage_bps)
    try:
        instructions, meta = build_flash_loan_tx(client, settings, cycle)
    except (JupiterError, AssertionError) as e:
        print(f"❌ تعذّر بناء المعاملة: {e}")
        return 1

    print(f"📦 المعاملة الذرّية ({' → '.join(cycle)}):")
    for i, ins in enumerate(instructions, 1):
        print(f"   {i}. [{ins.kind}] {ins.description}")
    print()

    ok, msg, ledger = simulate_tx(instructions, base)
    print(msg)

    borrow = from_atomic(meta["borrow_atomic"], base)
    fee = from_atomic(meta["flash_fee"], base)
    final = from_atomic(meta["final_amount"], base)
    if ok:
        profit = final - borrow - fee
        print(f"\n   مقترض: {borrow:,.2f} {base} | بعد الحلقة: {final:,.2f} {base}")
        print(f"   رسوم القرض: {fee:,.4f} {base} | صافي الربح: {profit:+,.4f} {base}")
        print(f"   رصيد {base} المتبقّي (الربح): "
              f"{from_atomic(ledger.balances.get(base, 0), base):,.4f}")
    else:
        print(f"\n   كما في سولانا الحقيقية: لا خسارة سوى رسوم الشبكة على "
              f"المعاملة الملغاة. رأس المال المقترض لم يكن حقيقياً أصلاً.")
        print(f"   (مقترض نظرياً {borrow:,.2f}، الحلقة أعادت {final:,.2f} "
              f"{base} — لا يكفي للسداد)")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
