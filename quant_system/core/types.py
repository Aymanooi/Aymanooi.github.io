"""
Core domain types shared across all layers.

These are deliberately small, immutable (`frozen=True`) dataclasses with explicit
fields and validation. They form the contract between layers so each layer can be
tested in isolation against well-defined inputs/outputs.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Market side & regimes ─────────────────────────────────────────────────────
class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Regime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOL = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"
    BREAKOUT = "breakout"
    MEAN_REVERTING = "mean_reverting"
    STRESSED = "stressed"          # abnormal — most strategies must stand down
    TRANSITION = "transition"
    UNKNOWN = "unknown"


# ── Data quality descriptor (mandated by spec, Phase 2) ───────────────────────
@dataclass(frozen=True)
class DataQuality:
    """Quality metadata that travels with every data batch.

    Scores are in [0, 1]. A batch whose `quality_score` or `reliability_score`
    falls below the configured floor MUST NOT drive a high-risk decision.
    """
    source_name: str
    freshness_seconds: float        # age of the most recent point
    quality_score: float            # completeness / cleanliness  [0,1]
    reliability_score: float        # historical trustworthiness of source [0,1]
    latency_estimate_ms: float
    coverage_score: float           # fraction of expected points present [0,1]

    def __post_init__(self) -> None:
        for name in ("quality_score", "reliability_score", "coverage_score"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0,1], got {v}")
        if self.freshness_seconds < 0 or self.latency_estimate_ms < 0:
            raise ValueError("freshness/latency cannot be negative")

    def is_tradeable(self, min_quality: float, min_reliability: float,
                     max_freshness_seconds: float) -> bool:
        """True only if the data is fresh and trustworthy enough to act on."""
        return (
            self.quality_score >= min_quality
            and self.reliability_score >= min_reliability
            and self.freshness_seconds <= max_freshness_seconds
        )


# ── Signal: the explainable output of a strategy ──────────────────────────────
@dataclass(frozen=True)
class Signal:
    """A strategy's proposal. Carries its own *explanation* (spec Phase 13)."""
    symbol: str
    side: Side
    strategy: str
    confidence: float                       # [0,1]
    regime: Regime
    entry_ref_price: float
    stop_loss_price: float
    take_profit_price: float
    reason: str                             # human-readable "why enter"
    invalidation: str                       # "why this would be wrong"
    created_ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        if self.entry_ref_price <= 0 or self.stop_loss_price <= 0:
            raise ValueError("prices must be positive")
        # Stop must be on the correct side of entry — a core safety invariant.
        if self.side is Side.BUY and self.stop_loss_price >= self.entry_ref_price:
            raise ValueError("BUY stop-loss must be below entry")
        if self.side is Side.SELL and self.stop_loss_price <= self.entry_ref_price:
            raise ValueError("SELL stop-loss must be above entry")

    @property
    def stop_distance_pct(self) -> float:
        return abs(self.entry_ref_price - self.stop_loss_price) / self.entry_ref_price

    @property
    def reward_risk(self) -> float:
        risk = abs(self.entry_ref_price - self.stop_loss_price)
        reward = abs(self.take_profit_price - self.entry_ref_price)
        return reward / risk if risk > 0 else 0.0
