"""
Risk limits — the single source of truth for "what is allowed".

The RiskEngine (Phase 6) reads these limits and is the *only* component permitted
to approve a trade. Limits are conservative by default and loaded from config so
they can be tightened without code changes. Nothing here promises profit; it only
constrains loss.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    # Per-trade
    max_risk_per_trade_pct: float = 0.01      # risk at most 1% of equity per trade
    min_reward_risk: float = 1.5              # reject setups with poor R:R

    # Aggregate loss caps (fractions of equity)
    max_daily_loss_pct: float = 0.03          # stop trading for the day at -3%
    max_weekly_loss_pct: float = 0.07
    max_drawdown_pct: float = 0.20            # kill switch at -20% from peak

    # Exposure
    max_open_positions: int = 1
    max_total_exposure_pct: float = 1.0       # gross notional / equity ceiling
    max_symbol_concentration_pct: float = 1.0
    max_correlation: float = 0.7              # block adding correlated exposure

    # Leverage (efficiency tool only — never a magic multiplier)
    max_leverage: float = 3.0
    liquidation_buffer_pct: float = 0.06      # require liq distance >= 6%

    # Behavioural guards
    loss_cooldown_trades: int = 3             # pause after N consecutive losses
    loss_cooldown_seconds: int = 1800

    # Market-quality gates
    min_data_quality: float = 0.80
    min_data_reliability: float = 0.80
    max_data_freshness_seconds: float = 120.0
    min_liquidity_usd_24h: float = 20_000_000.0

    def __post_init__(self) -> None:
        if not 0 < self.max_risk_per_trade_pct <= 0.05:
            raise ValueError("max_risk_per_trade_pct must be in (0, 0.05]")
        if self.max_leverage < 1:
            raise ValueError("max_leverage must be >= 1")
        if not 0 < self.max_daily_loss_pct < self.max_weekly_loss_pct:
            raise ValueError("daily loss cap must be positive and < weekly cap")
        if self.max_drawdown_pct <= 0:
            raise ValueError("max_drawdown_pct must be positive")

    def max_leverage_for_stop(self, stop_distance_pct: float) -> float:
        """Cap leverage so the stop sits inside the liquidation buffer.

        Liquidation distance ~= 1/leverage. We require it to exceed the buffer,
        i.e. leverage <= 1 / liquidation_buffer_pct, and never exceed max_leverage.
        """
        if stop_distance_pct <= 0:
            return 1.0
        buffer_cap = 1.0 / self.liquidation_buffer_pct
        return max(1.0, min(self.max_leverage, buffer_cap))
