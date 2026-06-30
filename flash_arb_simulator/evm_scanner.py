#!/usr/bin/env python3
"""
ماسح مراجحة متعدّد الشبكات (EVM) — Ethereum / Base / Arbitrum / BSC / Polygon.

يستخدم KyberSwap Aggregator API (عام، قراءة فقط) الذي يعيد — والأهم —
**تكلفة الغاز الفعلية بالدولار** مع كل اقتباس، فتصبح حسابات الربحية واقعية
تماماً وتشمل غاز كل تبديل.

الحلقة المفحوصة لكل عملة:  USDC → WETH → TOKEN → USDC
صافي الربح = (الناتج بالدولار − البدء بالدولار) − غاز التبديلات − رسوم القرض

⚠️  وضع المحاكاة فقط: قراءة أسعار، لا تنفيذ، لا مفاتيح خاصة.

الهدف: الإجابة بالدليل على "لنجرّب شبكة أخرى" — القيد (سوق فعّال + تكاليف
تنفيذ) موجود على كل شبكة، ويتغيّر شكله فقط: غاز إيثيريوم العالي يقتل الأفراد،
وفروق L2 الرخيصة أرفع من أن تُربح.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request


KYBER_URL = "https://aggregator-api.kyberswap.com/{chain}/api/v1/routes"

# مجموعات عملات لكل شبكة: العنوان + عدد المنازل العشرية.
# BASE = العملة الأساسية (مستقرّة)، WETH = الوسيط، والباقي للفحص.
CHAINS = {
    "ethereum": {
        "base": ("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        "weth": ("WETH", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
        "tokens": [
            ("WBTC", "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
            ("DAI", "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
            ("USDT", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
            ("LINK", "0x514910771AF9Ca656af840dff83E8264EcF986CA", 18),
            ("UNI", "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", 18),
            ("AAVE", "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9", 18),
            ("PEPE", "0x6982508145454Ce325dDbE47a25d4ec3d2311933", 18),
            ("SHIB", "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", 18),
        ],
    },
    "base": {
        "base": ("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
        "weth": ("WETH", "0x4200000000000000000000000000000000000006", 18),
        "tokens": [
            ("cbBTC", "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
            ("DAI", "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", 18),
            ("cbETH", "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", 18),
            ("AERO", "0x940181a94A35A4569E4529A3CDfB74e38FD98631", 18),
            ("DEGEN", "0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed", 18),
            ("BRETT", "0x532f27101965dd16442E59d40670FaF5eBB142E4", 18),
        ],
    },
    "arbitrum": {
        "base": ("USDC", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
        "weth": ("WETH", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", 18),
        "tokens": [
            ("WBTC", "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", 8),
            ("ARB", "0x912CE59144191C1204E64559FE8253a0e49E6548", 18),
            ("USDT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
            ("GMX", "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a", 18),
            ("LINK", "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4", 18),
        ],
    },
    "bsc": {
        "base": ("USDT", "0x55d398326f99059fF775485246999027B3197955", 18),
        "weth": ("WBNB", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", 18),
        "tokens": [
            ("USDC", "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", 18),
            ("ETH", "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", 18),
            ("BTCB", "0x7130d2A12B9BCBFAe4f2634d864A1Ee1Ce3Ead9c", 18),
            ("CAKE", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", 18),
            ("XRP", "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE", 18),
        ],
    },
    "polygon": {
        "base": ("USDC", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
        "weth": ("WETH", "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", 18),
        "tokens": [
            ("WMATIC", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", 18),
            ("WBTC", "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", 8),
            ("DAI", "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", 18),
            ("LINK", "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39", 18),
        ],
    },
}


def kyber_route(chain: str, token_in: str, amount_in: int,
                token_out: str, timeout: int = 25, retries: int = 3) -> dict:
    """يجلب أفضل مسار من KyberSwap. يعيد routeSummary (يشمل amountOut و gasUsd)."""
    params = {"tokenIn": token_in, "tokenOut": token_out,
              "amountIn": str(amount_in)}
    url = KYBER_URL.format(chain=chain) + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "flash-arb-simulator/1.0 (educational; read-only)",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") != 0 or "data" not in data:
                raise RuntimeError(data.get("message", "رد غير متوقع"))
            return data["data"]["routeSummary"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NoRoute()
            last = e
            time.sleep(2 ** attempt)
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"فشل بعد {retries} محاولات: {last}")


class NoRoute(Exception):
    pass


def scan_token(chain: str, base_addr: str, weth_addr: str,
               start_atomic: int, tok_addr: str) -> dict | None:
    """يفحص حلقة base → WETH → TOKEN → base ويعيد الاقتصاديات الحقيقية."""
    try:
        r1 = kyber_route(chain, base_addr, start_atomic, weth_addr)
        weth_amt = int(r1["amountOut"])
        r2 = kyber_route(chain, weth_addr, weth_amt, tok_addr)
        tok_amt = int(r2["amountOut"])
        r3 = kyber_route(chain, tok_addr, tok_amt, base_addr)
    except (NoRoute, RuntimeError):
        return None

    start_usd = float(r1["amountInUsd"])
    end_usd = float(r3["amountOutUsd"])
    gas_usd = (float(r1.get("gasUsd") or 0) + float(r2.get("gasUsd") or 0)
               + float(r3.get("gasUsd") or 0))
    gross = end_usd - start_usd
    return {"start_usd": start_usd, "end_usd": end_usd,
            "gross": gross, "gas_usd": gas_usd}


def main() -> int:
    p = argparse.ArgumentParser(
        description="ماسح مراجحة متعدّد الشبكات EVM (محاكاة فقط)")
    p.add_argument("--chain", default="base", choices=list(CHAINS.keys()),
                   help="الشبكة المراد فحصها")
    p.add_argument("--amount", type=float, default=10_000.0,
                   help="مبلغ البدء بالعملة الأساسية (USD تقريباً)")
    p.add_argument("--flash-fee-bps", type=float, default=5.0,
                   help="رسوم القرض الوميضي (Aave≈5، Balancer≈0)")
    p.add_argument("--delay", type=float, default=0.3,
                   help="تأخير بين الطلبات (ثوانٍ)")
    args = p.parse_args()

    cfg = CHAINS[args.chain]
    base_sym, base_addr, base_dec = cfg["base"]
    weth_sym, weth_addr, _ = cfg["weth"]
    start_atomic = int(round(args.amount * (10 ** base_dec)))

    print("=" * 72)
    print(f"🌐 ماسح مراجحة — شبكة: {args.chain.upper()} — وضع المحاكاة فقط")
    print("=" * 72)
    print(f"💰 الأساس: {base_sym} | البدء: {args.amount:,.0f} | "
          f"الوسيط: {weth_sym} | رسوم القرض: {args.flash_fee_bps} bps")
    print(f"🔍 فحص {len(cfg['tokens'])} عملة عبر {base_sym}→{weth_sym}→TOKEN→{base_sym}\n")

    flash_fee = args.amount * (args.flash_fee_bps / 10_000.0)
    rows = []
    for sym, addr, _dec in cfg["tokens"]:
        res = scan_token(args.chain, base_addr, weth_addr, start_atomic, addr)
        if res is None:
            print(f"  ⏭️  {sym}: تخطّي (لا مسار)")
            time.sleep(args.delay)
            continue
        net = res["gross"] - res["gas_usd"] - flash_fee
        rows.append((sym, res, net))
        flag = "✅" if net > 0 else "❌"
        sign = "+" if net >= 0 else ""
        print(f"  {flag} {base_sym}→{weth_sym}→{sym}→{base_sym:<6} "
              f"إجمالي: {res['gross']:+8.4f}$ | غاز: {res['gas_usd']:7.4f}$ | "
              f"قرض: {flash_fee:6.3f}$ | صافي: {sign}{net:.4f}$")
        time.sleep(args.delay)

    rows.sort(key=lambda x: x[2], reverse=True)
    wins = [r for r in rows if r[2] > 0]

    print("\n" + "-" * 72)
    if wins:
        print(f"🎯 {len(wins)} حلقة موجبة (نظرياً، قبل المنافسة):")
        for sym, _res, net in wins:
            print(f"   ✅ {sym}: +{net:.4f}$")
        print("\n⚠️  تعيش أجزاء من الثانية وتلتقطها بوتات MEV (Flashbots) قبلك.")
    else:
        print(f"😐 صفر فرص مربحة على {args.chain.upper()} "
              f"(فُحصت {len(rows)} حلقة).")
    print("-" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
