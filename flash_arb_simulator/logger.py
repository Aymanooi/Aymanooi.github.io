"""
تسجيل نتائج كل فحص في ملف CSV لمراقبة الفرص عبر الزمن وتحليلها لاحقاً.

كل سطر = نتيجة حلقة واحدة في لحظة زمنية واحدة. آمن تماماً (كتابة محلية فقط).
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone


CSV_FIELDS = [
    "timestamp_utc",
    "base_token",
    "cycle",
    "start_amount",
    "end_amount",
    "gross_profit",
    "total_fees",
    "net_profit",
    "net_profit_pct",
    "max_price_impact_pct",
    "is_opportunity",
    "sol_price_in_base",
    "flash_fee_bps",
]


class CsvLogger:
    def __init__(self, path: str):
        self.path = path
        self._ensure_header()

    def _ensure_header(self) -> None:
        need_header = (not os.path.exists(self.path)
                       or os.path.getsize(self.path) == 0)
        if need_header:
            with open(self.path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()

    def log(self, result, base_token: str, sol_price_in_base: float,
            flash_fee_bps: float, ts: str | None = None) -> None:
        if ts is None:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = {
            "timestamp_utc": ts,
            "base_token": base_token,
            "cycle": " -> ".join(result.cycle),
            "start_amount": f"{result.start_amount:.6f}",
            "end_amount": f"{result.end_amount:.6f}",
            "gross_profit": f"{result.gross_profit:.6f}",
            "total_fees": f"{result.total_fees:.6f}",
            "net_profit": f"{result.net_profit:.6f}",
            "net_profit_pct": f"{result.net_profit_pct:.6f}",
            "max_price_impact_pct": f"{result.max_price_impact_pct:.6f}",
            "is_opportunity": "1" if result.net_profit > 0 else "0",
            "sol_price_in_base": f"{sol_price_in_base:.6f}",
            "flash_fee_bps": f"{flash_fee_bps:.2f}",
        }
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(row)
