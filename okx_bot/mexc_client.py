"""عميل MEXC Futures (العقود الدائمة) — بنفس واجهة OKXClient تماماً.

MEXC أعادت فتح API العقود للتداول في 31 مارس 2026 (KYC مطلوب).
هذا العميل يوفّر نفس دوال OKXClient وبنفس صيغ الإرجاع، فيعمل باقي
البوت (run_once.py) دون أي تعديل عند ضبط EXCHANGE=mexc.

التوقيع (خاص/private): HMAC-SHA256 على (accessKey + Request-Time +
parameterString)، مع الرؤوس: ApiKey / Request-Time / Signature.
  • GET/DELETE: parameterString = بارامترات مرتّبة أبجدياً «k=v&k=v».
  • POST: parameterString = جسم JSON الخام.

الرموز على MEXC بصيغة «BTC_USDT» (لا «BTC-USDT-SWAP»).
مصدر: https://mexcdevelop.github.io/apidocs/contract_v1_en/
"""
import time
import math
import json
import hmac
import hashlib
import urllib.request
import urllib.parse

BASE = "https://contract.mexc.com"

# خرائط تحويل إطار الشموع OKX → MEXC
_BAR_MAP = {
    "1m": "Min1", "5m": "Min5", "15m": "Min15", "30m": "Min30",
    "1H": "Min60", "1h": "Min60", "4H": "Hour4", "1D": "Day1",
}


class MEXCClient:
    def __init__(self, api_key, api_secret, passphrase=None, is_demo="0"):
        # passphrase غير مستخدم في MEXC (يُقبل للتوافق مع نفس التوقيع)
        self.key = api_key or ""
        self.secret = (api_secret or "").encode()
        # كاش تفاصيل العقود (contractSize/tick/lot/maxLev) لتقليل النداءات
        self._detail_cache = {}

    # ── HTTP / التوقيع ────────────────────────────────────────────────
    def _sign(self, ts, param_str):
        target = f"{self.key}{ts}{param_str}"
        return hmac.new(self.secret, target.encode(), hashlib.sha256).hexdigest()

    def _get(self, path, params=None, private=False):
        params = params or {}
        qs = ""
        if params:
            items = sorted(params.items())
            qs = "&".join(f"{k}={v}" for k, v in items)
        url = f"{BASE}{path}" + (f"?{qs}" if qs else "")
        headers = {"Content-Type": "application/json"}
        if private:
            ts = str(int(time.time() * 1000))
            headers.update({
                "ApiKey": self.key,
                "Request-Time": ts,
                "Signature": self._sign(ts, qs),
            })
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            return {"success": False, "code": -1, "msg": str(e), "data": None}

    def _post(self, path, body):
        body_str = json.dumps(body, separators=(",", ":"))
        ts = str(int(time.time() * 1000))
        headers = {
            "Content-Type": "application/json",
            "ApiKey": self.key,
            "Request-Time": ts,
            "Signature": self._sign(ts, body_str),
        }
        req = urllib.request.Request(f"{BASE}{path}", data=body_str.encode(),
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read())
            except Exception:
                return {"success": False, "code": e.code, "msg": str(e)}
        except Exception as e:
            return {"success": False, "code": -1, "msg": str(e)}

    # ── تفاصيل العقد (contractSize / tickSz / lotSz / maxLev) ──────────
    def _detail(self, symbol):
        if symbol in self._detail_cache:
            return self._detail_cache[symbol]
        r = self._get("/api/v1/contract/detail", {"symbol": symbol})
        data = r.get("data")
        if isinstance(data, list):
            data = data[0] if data else None
        if data:
            self._detail_cache[symbol] = data
        return data

    # ── السوق ─────────────────────────────────────────────────────────
    def get_top_pairs(self, count=50, min_usd_vol=0):
        """أعلى عقود USDT سيولةً (amount24 بالدولار مباشرة)."""
        r = self._get("/api/v1/contract/ticker")
        data = r.get("data") or []
        rows = []
        for t in data:
            sym = t.get("symbol", "")
            if not sym.endswith("_USDT"):
                continue
            usd_vol = float(t.get("amount24", 0) or 0)   # amount24 = حجم بالدولار
            if usd_vol >= min_usd_vol:
                rows.append((sym, usd_vol))
        rows.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in rows[:count]]

    def get_candles(self, inst_id, bar="15m", limit=60):
        """شموع MEXC تُرجَع كأعمدة (time[],open[],...) — نحوّلها لصفوف
        [[ts,o,h,l,c,vol], ...] بنفس صيغة OKX التي يتوقّعها analyze."""
        interval = _BAR_MAP.get(bar, "Min1")
        r = self._get(f"/api/v1/contract/kline/{inst_id}",
                      {"interval": interval})
        d = r.get("data") or {}
        t = d.get("time") or []
        if not t:
            return []
        o, h, l, c = d.get("open", []), d.get("high", []), d.get("low", []), d.get("close", [])
        v = d.get("vol", [])
        rows = []
        for i in range(len(t)):
            rows.append([
                int(t[i]) * 1000, str(o[i]), str(h[i]),
                str(l[i]), str(c[i]), str(v[i] if i < len(v) else 0),
            ])
        return rows[-limit:]

    def get_ticker(self, inst_id):
        r = self._get("/api/v1/contract/ticker", {"symbol": inst_id})
        d = r.get("data")
        if isinstance(d, list):
            d = d[0] if d else None
        if not d:
            return None
        # نطبّع لصيغة OKX: {"last": ...}
        return {"last": str(d.get("lastPrice", 0)), "_raw": d}

    def get_change_map(self):
        """riseFallRate = تغيّر 24س ككسر → نضربه ×100."""
        r = self._get("/api/v1/contract/ticker")
        data = r.get("data") or []
        out = {}
        for t in data:
            sym = t.get("symbol", "")
            if not sym.endswith("_USDT"):
                continue
            rf = t.get("riseFallRate")
            if rf is not None:
                try:
                    out[sym] = float(rf) * 100.0
                except (ValueError, TypeError):
                    pass
        return out

    # ── الحساب ────────────────────────────────────────────────────────
    def _usdt_asset(self):
        r = self._get("/api/v1/private/account/assets", private=True)
        for a in (r.get("data") or []):
            if a.get("currency") == "USDT":
                return a
        return None

    def get_balance(self):
        a = self._usdt_asset()
        if not a:
            return 0.0
        try:
            return float(a.get("availableBalance", 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    def get_total_equity(self):
        a = self._usdt_asset()
        if not a:
            return 0.0
        try:
            return float(a.get("equity", 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    # ── معلومات العقد / الرافعة ────────────────────────────────────────
    def get_instrument_info(self, inst_id):
        """نطبّع لصيغة OKX: ctVal/lotSz/minSz/tickSz/lever."""
        d = self._detail(inst_id)
        if not d:
            return None
        return {
            "ctVal": d.get("contractSize", 1),
            "lotSz": d.get("volUnit", 1),
            "minSz": d.get("minVol", d.get("volUnit", 1)),
            "tickSz": d.get("priceUnit", 0),
            "lever": d.get("maxLeverage", 0),
        }

    def get_max_leverage(self, inst_id):
        d = self._detail(inst_id)
        if not d:
            return None
        try:
            lv = float(d.get("maxLeverage", 0))
            return lv if lv > 0 else None
        except (ValueError, TypeError):
            return None

    def set_leverage(self, inst_id, leverage):
        # في MEXC تُمرَّر الرافعة داخل أمر الفتح نفسه (leverage) — لا نداء منفصل
        # مطلوب في وضع cross. نحفظها للاستخدام في place_order.
        self._pending_lev = int(leverage)

    # ── المراكز ───────────────────────────────────────────────────────
    def _map_position(self, p):
        """نطبّع مركز MEXC لصيغة OKX: pos(موقّع)/instId/avgPx/upl/side."""
        vol = float(p.get("holdVol", 0) or 0)
        ptype = int(p.get("positionType", 0))  # 1 long, 2 short
        signed = vol if ptype == 1 else -vol
        return {
            "instId": p.get("symbol", ""),
            "pos": signed,
            "avgPx": float(p.get("holdAvgPrice", 0) or 0),
            "upl": float(p.get("realized", 0) or p.get("unrealized", 0) or 0),
            "side": "long" if ptype == 1 else "short",
            "_raw": p,
        }

    def get_all_positions(self):
        r = self._get("/api/v1/private/position/open_positions", private=True)
        out = []
        for p in (r.get("data") or []):
            if float(p.get("holdVol", 0) or 0) != 0:
                out.append(self._map_position(p))
        return out

    def get_position(self, inst_id):
        for p in self.get_all_positions():
            if p["instId"] == inst_id:
                return p
        return None

    def get_pending_orders(self):
        r = self._get("/api/v1/private/order/list/open_orders", private=True)
        data = r.get("data") or []
        # نطبّع: {"instId":..., "ordId":...}
        return [{"instId": o.get("symbol", ""), "ordId": str(o.get("orderId", ""))}
                for o in data]

    def cancel_order(self, inst_id, ord_id):
        r = self._post("/api/v1/private/order/cancel", [int(ord_id)])
        return bool(r.get("success"))

    def get_last_realized_pnl(self, inst_id):
        r = self._get("/api/v1/private/position/list/history_positions",
                      {"symbol": inst_id, "page_num": 1, "page_size": 5},
                      private=True)
        data = r.get("data") or []
        if not data:
            return None
        try:
            return float(data[0].get("realised", data[0].get("realized", 0)))
        except (ValueError, TypeError):
            return None

    # ── حساب الحجم ────────────────────────────────────────────────────
    def calculate_contracts(self, inst_id, balance, price, leverage, capital_ratio):
        d = self._detail(inst_id)
        if not d:
            return 0
        ct_val = float(d.get("contractSize", 1) or 1)
        lot = float(d.get("volUnit", 1) or 1)
        min_v = float(d.get("minVol", lot) or lot)
        usdt = balance * capital_ratio
        contracts = (usdt * leverage) / (price * ct_val)
        contracts = math.floor(contracts / lot) * lot
        if contracts < min_v:
            contracts = min_v
        notional = contracts * ct_val * price
        if notional / leverage > balance:
            return 0
        return contracts

    def _round_to_tick(self, price, tick_sz):
        from decimal import Decimal, ROUND_HALF_UP
        if not tick_sz:
            return price
        tick_d = Decimal(str(tick_sz))
        p = (Decimal(str(price)) / tick_d).quantize(Decimal("1"),
             rounding=ROUND_HALF_UP) * tick_d
        return float(p)

    # ── الأوامر ───────────────────────────────────────────────────────
    def _submit(self, symbol, side_code, vol, price, order_type, sl=None, tp=None):
        lev = getattr(self, "_pending_lev", 20)
        body = {
            "symbol": symbol,
            "vol": vol,
            "side": side_code,          # 1 فتح شراء، 3 فتح بيع، 2/4 إغلاق
            "type": order_type,         # 5 سوق، 1 حدّي
            "openType": 2,              # 2 = cross
            "leverage": lev,
        }
        if price is not None:
            body["price"] = price
        if sl is not None:
            body["stopLossPrice"] = sl
        if tp is not None:
            body["takeProfitPrice"] = tp
        # نطبّع الرد لصيغة OKX: {"code":"0"} عند النجاح
        r = self._post("/api/v1/private/order/create", body)
        ok = bool(r.get("success")) and r.get("code") in (0, "0", None)
        return {"code": "0" if ok else str(r.get("code", "1")),
                "msg": r.get("message", r.get("msg", "")),
                "data": [r.get("data", {})]}

    def place_order(self, inst_id, side, sz, entry_price, sl_pct, tp_pct,
                    sl_override=None, tp_override=None):
        if sl_override and tp_override:
            sl_price, tp_price = sl_override, tp_override
        elif side == "buy":
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
        else:
            sl_price = entry_price * (1 + sl_pct)
            tp_price = entry_price * (1 - tp_pct)
        info = self.get_instrument_info(inst_id)
        tick = float(info.get("tickSz", 0)) if info else 0
        sl_price = self._round_to_tick(sl_price, tick)
        tp_price = self._round_to_tick(tp_price, tick)
        side_code = 1 if side == "buy" else 3   # فتح شراء / فتح بيع
        return self._submit(inst_id, side_code, sz, None, 5,
                            sl=sl_price, tp=tp_price)

    def place_order_maker(self, inst_id, side, sz, ref_price,
                          sl_override, tp_override, offset=0.0005):
        info = self.get_instrument_info(inst_id)
        tick = float(info.get("tickSz", 0)) if info else 0
        px = ref_price * (1 - offset) if side == "buy" else ref_price * (1 + offset)
        px = self._round_to_tick(px, tick)
        sl_price = self._round_to_tick(sl_override, tick)
        tp_price = self._round_to_tick(tp_override, tick)
        side_code = 1 if side == "buy" else 3
        return self._submit(inst_id, side_code, sz, px, 2,  # 2 = Post Only
                            sl=sl_price, tp=tp_price)

    def place_order_no_sltp(self, inst_id, side, sz):
        side_code = 1 if side == "buy" else 3
        return self._submit(inst_id, side_code, sz, None, 5)

    def close_position(self, inst_id):
        p = self.get_position(inst_id)
        if not p:
            return True
        vol = abs(float(p["pos"]))
        # إغلاق: إن كان المركز شراءً (long) نغلقه ببيع=4، والبيع بإغلاق شراء=2
        close_code = 4 if p["pos"] > 0 else 2
        r = self._submit(inst_id, close_code, vol, None, 5)
        return r["code"] == "0"
