import time
import math
import okx.Trade as Trade
import okx.Account as Account
import okx.MarketData as Market
import okx.PublicData as PublicData


class OKXClient:
    def __init__(self, api_key, api_secret, passphrase, is_demo="1"):
        flag = is_demo
        self.trade_api = Trade.TradeAPI(api_key, api_secret, passphrase, False, flag)
        self.account_api = Account.AccountAPI(api_key, api_secret, passphrase, False, flag)
        self.market_api = Market.MarketAPI(flag=flag)
        self.public_api = PublicData.PublicAPI(flag=flag)

    def get_top_pairs(self, count=50):
        result = self.market_api.get_tickers(instType="SWAP")
        if result["code"] != "0":
            return []
        tickers = [t for t in result["data"] if t["instId"].endswith("-USDT-SWAP")]
        # فلتر: السعر > $0.10 لتجنب العملات الصغيرة جداً التي ترفضها OKX
        tickers = [t for t in tickers if float(t.get("last", 0)) >= 0.10]
        tickers.sort(key=lambda x: float(x.get("volCcy24h", 0)), reverse=True)
        return [t["instId"] for t in tickers[:count]]

    def get_candles(self, inst_id, bar="15m", limit=60):
        result = self.market_api.get_candlesticks(instId=inst_id, bar=bar, limit=str(limit))
        if result["code"] != "0":
            return []
        # [[ts, open, high, low, close, vol, volCcy], ...]
        return result["data"]

    def get_ticker(self, inst_id):
        result = self.market_api.get_ticker(instId=inst_id)
        if result["code"] != "0" or not result["data"]:
            return None
        return result["data"][0]

    def get_balance(self):
        result = self.account_api.get_account_balance(ccy="USDT")
        if result["code"] != "0":
            return 0.0
        for detail in result["data"][0].get("details", []):
            if detail["ccy"] == "USDT":
                return float(detail["availBal"])
        return 0.0

    def get_instrument_info(self, inst_id):
        result = self.public_api.get_instruments(instType="SWAP", instId=inst_id)
        if result["code"] != "0" or not result["data"]:
            return None
        return result["data"][0]

    def get_max_leverage(self, inst_id):
        """أقصى رافعة تسمح بها هذه العملة (بعض العملات حدّها 10x فقط)."""
        info = self.get_instrument_info(inst_id)
        if not info:
            return None
        try:
            lever = float(info.get("lever", 0))
            return lever if lever > 0 else None
        except (ValueError, TypeError):
            return None

    def set_leverage(self, inst_id, leverage):
        self.account_api.set_leverage(
            instId=inst_id,
            lever=str(leverage),
            mgnMode="cross"
        )

    def get_all_positions(self):
        result = self.account_api.get_positions(instType="SWAP")
        if result["code"] != "0":
            return []
        return [p for p in result["data"] if float(p.get("pos", "0")) != 0]

    def get_position(self, inst_id):
        result = self.account_api.get_positions(instType="SWAP", instId=inst_id)
        if result["code"] != "0" or not result["data"]:
            return None
        pos = result["data"][0]
        if float(pos.get("pos", "0")) == 0:
            return None
        return pos

    def get_last_realized_pnl(self, inst_id):
        """
        الربح/الخسارة المحقّق فعلياً لآخر مركز مُغلق على هذه العملة.
        يُستخدم لتعليم الدماغ من النتيجة الحقيقية بدل تقريب سعر السوق.
        يُرجع float أو None إذا لم تتوفّر البيانات.
        """
        try:
            result = self.account_api.get_positions_history(
                instType="SWAP", instId=inst_id, limit="5")
            if result["code"] != "0" or not result["data"]:
                return None
            # الأحدث أولاً — حقل realizedPnl (أو pnl كبديل)
            row = result["data"][0]
            val = row.get("realizedPnl", row.get("pnl", ""))
            return float(val) if val not in ("", None) else None
        except Exception:
            return None

    def calculate_contracts(self, inst_id, balance, price, leverage, capital_ratio):
        info = self.get_instrument_info(inst_id)
        if not info:
            return 0
        ct_val = float(info.get("ctVal", 1))
        lot_sz = float(info.get("lotSz", 1))
        min_sz = float(info.get("minSz", lot_sz))
        usdt_to_use = balance * capital_ratio
        contracts = (usdt_to_use * leverage) / (price * ct_val)
        contracts = math.floor(contracts / lot_sz) * lot_sz
        # تأكد من تلبية الحد الأدنى للطلب
        if contracts < min_sz:
            contracts = min_sz
        # الهامش المطلوب لهذا الحجم — لو تجاوز الرصيد، تخطّ العملة (ترجع 0)
        notional      = contracts * ct_val * price
        margin_needed = notional / leverage
        if margin_needed > balance:
            return 0
        return contracts

    def _round_to_tick(self, price, tick_sz):
        """Round price to the nearest valid tick size using Decimal for precision."""
        from decimal import Decimal, ROUND_HALF_UP
        tick_d  = Decimal(str(tick_sz))
        price_d = Decimal(str(price))
        rounded = (price_d / tick_d).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick_d
        return float(rounded)

    def place_order(self, inst_id, side, sz, entry_price, sl_pct, tp_pct,
                    sl_override=None, tp_override=None):
        if sl_override and tp_override:
            sl_price = sl_override
            tp_price = tp_override
        elif side == "buy":
            sl_price = round(entry_price * (1 - sl_pct), 8)
            tp_price = round(entry_price * (1 + tp_pct), 8)
        else:
            sl_price = round(entry_price * (1 + sl_pct), 8)
            tp_price = round(entry_price * (1 - tp_pct), 8)

        # Round SL/TP to instrument tickSz — avoids "All operations failed"
        info    = self.get_instrument_info(inst_id)
        tick_sz = float(info.get("tickSz", 0)) if info else 0
        if tick_sz > 0:
            sl_price = self._round_to_tick(sl_price, tick_sz)
            tp_price = self._round_to_tick(tp_price, tick_sz)

        result = self.trade_api.place_order(
            instId=inst_id,
            tdMode="cross",
            side=side,
            ordType="market",
            sz=str(sz),
            attachAlgoOrds=[{
                "attachAlgoClOrdId": f"b{int(time.time() * 1000) % (10 ** 15)}",
                "tpTriggerPx": str(tp_price),
                "tpOrdPx": "-1",
                "slTriggerPx": str(sl_price),
                "slOrdPx": "-1",
            }]
        )
        return result

    def place_order_no_sltp(self, inst_id, side, sz):
        """Plain market order without SL/TP — fallback when attached algo fails."""
        result = self.trade_api.place_order(
            instId=inst_id,
            tdMode="cross",
            side=side,
            ordType="market",
            sz=str(sz),
        )
        return result

    def close_position(self, inst_id):
        result = self.trade_api.close_positions(
            instId=inst_id,
            mgnMode="cross"
        )
        return result["code"] == "0"
