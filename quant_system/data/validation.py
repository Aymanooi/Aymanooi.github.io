"""
Data validation layer (spec Phase 2).

Takes a raw OHLCV batch and returns (cleaned_batch, DataQuality). It never throws
on merely-imperfect data — instead it *scores* the data. Downstream, the risk
engine refuses to trade when the score is below the configured floor (fail closed).

Checks:
  * monotonic, de-duplicated timestamps
  * time gaps vs the expected cadence  → coverage_score
  * dropped/duplicate candles          → quality_score
  * outliers (extreme bar-to-bar jumps, zero volume runs)
  * freshness (age of last candle)     → freshness_seconds
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from core.types import DataQuality
from data.ohlcv import OHLCVBatch, Candle, timeframe_to_ms


@dataclass(frozen=True)
class ValidationReport:
    batch: OHLCVBatch
    quality: DataQuality
    n_duplicates: int
    n_gaps: int
    n_outliers: int
    notes: tuple[str, ...]


def validate(batch: OHLCVBatch, *, source_name: str = "okx",
             reliability_score: float = 0.9, latency_estimate_ms: float = 50.0,
             outlier_jump_pct: float = 0.25, now_ms: int | None = None
             ) -> ValidationReport:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    step = timeframe_to_ms(batch.timeframe)
    candles = list(batch.candles)
    notes: list[str] = []

    if not candles:
        q = DataQuality(source_name, 1e9, 0.0, reliability_score, latency_estimate_ms, 0.0)
        return ValidationReport(batch, q, 0, 0, 0, ("empty batch",))

    # 1) de-duplicate by timestamp (keep first), ensure ascending
    seen: dict[int, Candle] = {}
    duplicates = 0
    for c in candles:
        if c.ts in seen:
            duplicates += 1
        else:
            seen[c.ts] = c
    clean = [seen[ts] for ts in sorted(seen)]
    if duplicates:
        notes.append(f"{duplicates} duplicate timestamps dropped")

    # 2) gaps: expected span vs present candles → coverage
    span = clean[-1].ts - clean[0].ts
    expected = span // step + 1 if span >= 0 else 1
    present = len(clean)
    gaps = max(0, expected - present)
    coverage = present / expected if expected > 0 else 1.0
    if gaps:
        notes.append(f"{gaps} missing candles (coverage {coverage:.1%})")

    # 3) outliers: implausible bar-to-bar close jumps, zero-volume bars
    outliers = 0
    for prev, cur in zip(clean, clean[1:]):
        if prev.close > 0 and abs(cur.close / prev.close - 1) > outlier_jump_pct:
            outliers += 1
    zero_vol = sum(1 for c in clean if c.volume == 0)
    if outliers:
        notes.append(f"{outliers} extreme price jumps (>{outlier_jump_pct:.0%})")
    if zero_vol:
        notes.append(f"{zero_vol} zero-volume bars")

    # 4) scoring  (penalise dupes, gaps, outliers, zero-volume)
    n = present
    quality_score = max(0.0, 1.0
                        - (duplicates / n)
                        - (outliers / n) * 2.0      # outliers weigh double
                        - (zero_vol / n) * 0.5)
    quality_score = min(1.0, quality_score)
    freshness = max(0.0, (now_ms - clean[-1].ts) / 1000.0)

    quality = DataQuality(
        source_name=source_name,
        freshness_seconds=freshness,
        quality_score=round(quality_score, 4),
        reliability_score=reliability_score,
        latency_estimate_ms=latency_estimate_ms,
        coverage_score=round(min(1.0, coverage), 4),
    )
    cleaned = OHLCVBatch(batch.symbol, batch.timeframe, tuple(clean))
    return ValidationReport(cleaned, quality, duplicates, gaps, outliers, tuple(notes))
