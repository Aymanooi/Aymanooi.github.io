"""
عميل OKX الموقّع — نسخة مُصلحة وآمنة من okx_super_bot.py المرفوع.

الإصلاحات الجوهرية مقارنةً بالملف الأصلي:
  ① المفاتيح من متغيرات البيئة فقط (OKX_API_KEY / OKX_SECRET_KEY /
     OKX_PASSPHRASE) — لا تُكتب في الكود أبدًا ولا تُرفع إلى Git.
  ② وضع Demo (المحاكاة الرسمية من OKX) هو الافتراضي الإجباري.
     التداول الحقيقي يتطلب ضبط OKX_LIVE=I_ACCEPT_FULL_RISK يدويًا.
  ③ توقيع GET يشمل سلسلة الاستعلام (كما تتطلب OKX — كان ناقصًا).
  ④ سقف رافعة إجباري 3x بدل 50x (رافعة 50x = تصفية عند حركة 2% فقط).
  ⑤ فك ترميز التوقيع إلى نص (كان bytes خامًا).
"""
import base64
import datetime
import hmac
import json
import logging
import os
from urllib.parse import urlencode

import requests

logger = logging.getLogger("okx_client")

MAX_SAFE_LEVERAGE = 3          # سقف صارم — لا يُتجاوز برمجيًا
BASE_URL = "https://www.okx.com"


class OKXClient:
    def __init__(self):
        self.api_key = os.environ.get("OKX_API_KEY", "")
        self.secret_key = os.environ.get("OKX_SECRET_KEY", "")
        self.passphrase = os.environ.get("OKX_PASSPHRASE", "")
        # التداول الحقيقي يتطلب إقرارًا صريحًا بالمخاطرة عبر متغير بيئة
        self.demo = os.environ.get("OKX_LIVE", "") != "I_ACCEPT_FULL_RISK"
        self.session = requests.Session()
        if not all([self.api_key, self.secret_key, self.passphrase]):
            logger.warning("مفاتيح OKX غير مضبوطة في البيئة — وضع القراءة العامة فقط.")

    # ---------- التوقيع ----------
    def _timestamp(self):
        return datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z"

    def _sign(self, ts, method, path, body=""):
        msg = f"{ts}{method.upper()}{path}{body}"
        mac = hmac.new(self.secret_key.encode(), msg.encode(), digestmod="sha256")
        return base64.b64encode(mac.digest()).decode()

    def _request(self, method, path, params=None, body=None):
        # توقيع GET يجب أن يشمل سلسلة الاستعلام (إصلاح للملف الأصلي)
        if method == "GET" and params:
            path = f"{path}?{urlencode(params)}"
            params = None
        body_str = json.dumps(body) if body else ""
        ts = self._timestamp()
        headers = {
            "CONTENT-TYPE": "application/json",
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": self._sign(ts, method, path, body_str),
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }
        if self.demo:
            headers["x-simulated-trading"] = "1"   # محاكاة OKX الرسمية
        url = BASE_URL + path
        resp = self.session.request(
            method, url, headers=headers,
            data=body_str if body else None, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("code") not in ("0", 0, None):
            logger.error("OKX error %s: %s", payload.get("code"), payload.get("msg"))
        return payload

    # ---------- عمليات الحساب ----------
    def balance(self):
        return self._request("GET", "/api/v5/account/balance")

    def set_leverage(self, inst_id, lever, mgn_mode="isolated"):
        lever = min(int(lever), MAX_SAFE_LEVERAGE)   # السقف الإجباري
        body = {"instId": inst_id, "lever": str(lever), "mgnMode": mgn_mode}
        return self._request("POST", "/api/v5/account/set-leverage", body=body)

    def positions(self, inst_id=None):
        params = {"instId": inst_id} if inst_id else None
        return self._request("GET", "/api/v5/account/positions", params=params)

    # ---------- الأوامر ----------
    def market_order(self, inst_id, side, sz, pos_side,
                     sl_trigger=None, tp_trigger=None):
        """أمر سوق مع وقف خسارة وجني أرباح مرفقين (إلزاميان عمليًا)."""
        body = {
            "instId": inst_id,
            "tdMode": "isolated",     # عزل الهامش: الخسارة القصوى = هامش الصفقة فقط
            "side": side,
            "posSide": pos_side,
            "ordType": "market",
            "sz": str(sz),
        }
        algo = []
        if sl_trigger:
            algo.append({"slTriggerPx": str(sl_trigger), "slOrdPx": "-1"})
        if tp_trigger:
            algo.append({"tpTriggerPx": str(tp_trigger), "tpOrdPx": "-1"})
        if algo:
            body["attachAlgoOrds"] = algo
        mode = "DEMO" if self.demo else "LIVE"
        logger.info("[%s] %s %s sz=%s", mode, side, inst_id, sz)
        return self._request("POST", "/api/v5/trade/order", body=body)
