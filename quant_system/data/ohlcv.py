"""
OHLCV domain types — the canonical candle representation used system-wide.

Timestamps are epoch milliseconds (UTC). Batches are immutable and always sorted
ascending by time so downstream layers never have to re-sort or worry about TZ.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Candle:
    ts: int          # epoch ms, UTC, open time
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("inconsistent OHLC: high/low do not bound open/close")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")


@dataclass(frozen=True)
class OHLCVBatch:
    symbol: str
    timeframe: str
    candles: tuple[Candle, ...]

    @property
    def closes(self) -> list[float]:
        return [c.close for c in self.candles]

    def __len__(self) -> int:
        return len(self.candles)


def timeframe_to_ms(timeframe: str) -> int:
    """Convert '1m','5m','15m','1H','4H','1D' → milliseconds."""
    unit = timeframe[-1].lower()
    qty = int(timeframe[:-1])
    factor = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}.get(unit)
    if factor is None:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return qty * factor


def build_batch(symbol: str, timeframe: str,
                rows: Sequence[Sequence[float]]) -> OHLCVBatch:
    """Build a sorted, validated batch from raw [ts,o,h,l,c,v] rows."""
    candles = tuple(
        Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
        for r in rows
    )
    candles = tuple(sorted(candles, key=lambda c: c.ts))
    return OHLCVBatch(symbol, timeframe, candles)
