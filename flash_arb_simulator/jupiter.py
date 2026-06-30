"""
عميل بسيط لواجهة Jupiter Quote API.

يستخدم فقط نقطة النهاية /quote (قراءة الأسعار). لا يبني ولا يوقّع ولا يرسل
أي معاملة. لا حاجة لأي مفتاح خاص.
"""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
import json


class JupiterError(Exception):
    pass


class NoRouteError(JupiterError):
    """لا يوجد مسار تبديل (سيولة غير كافية لهذا الحجم) — لا فائدة من إعادة المحاولة."""


class JupiterClient:
    def __init__(self, base_url: str, slippage_bps: int = 50, timeout: int = 25):
        self.base_url = base_url.rstrip("/")
        self.slippage_bps = slippage_bps
        self.timeout = timeout

    def quote(self, input_mint: str, output_mint: str, amount: int,
              retries: int = 3) -> dict:
        """
        يجلب اقتباساً لتبديل `amount` (وحدات ذرية) من input_mint إلى output_mint.
        يعيد قاموس الاستجابة كما هو من Jupiter.
        """
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(self.slippage_bps),
            # نمنع التقسيم عبر وسطاء غير مباشرين للحفاظ على واقعية الحلقة
            "restrictIntermediateTokens": "true",
        }
        url = f"{self.base_url}/quote?" + urllib.parse.urlencode(params)

        last_err = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(
                    url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if "outAmount" not in data:
                    raise JupiterError(f"رد غير متوقع: {data}")
                return data
            except urllib.error.HTTPError as e:
                # 4xx = خطأ منطقي (غالباً لا مسار) — اقرأ السبب ولا تُعد المحاولة
                body = ""
                try:
                    body = e.read().decode("utf-8")
                except Exception:
                    pass
                if 400 <= e.code < 500:
                    if "NO_ROUTES_FOUND" in body or "No routes" in body:
                        raise NoRouteError("لا مسار (سيولة غير كافية لهذا الحجم)")
                    raise JupiterError(f"HTTP {e.code}: {body[:200]}")
                last_err = e
                time.sleep(2 ** attempt)
            except Exception as e:  # شبكة/تحليل — أعد المحاولة
                last_err = e
                time.sleep(2 ** attempt)
        raise JupiterError(f"فشل جلب الاقتباس بعد {retries} محاولات: {last_err}")
