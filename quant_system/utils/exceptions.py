"""
Exception hierarchy for the trading system.

Every layer raises a typed exception so failures are explicit, catchable at the
right boundary, and never silently swallowed. Risk-sensitive code paths must
*fail closed* (refuse to trade) rather than fail open.
"""
from __future__ import annotations


class TradingSystemError(Exception):
    """Base class for every error raised by the system."""


# ── Data layer ────────────────────────────────────────────────────────────────
class DataError(TradingSystemError):
    """Base for data ingestion / validation failures."""


class DataQualityError(DataError):
    """Raised when data is too low-quality to drive a decision (fail closed)."""


class DataGapError(DataError):
    """Missing candles / time gaps that exceed the allowed tolerance."""


# ── Configuration ─────────────────────────────────────────────────────────────
class ConfigError(TradingSystemError):
    """Invalid or missing configuration."""


class MissingCredentialError(ConfigError):
    """A required secret (API key/secret/passphrase) is absent."""


# ── Risk layer (these must block trading) ─────────────────────────────────────
class RiskError(TradingSystemError):
    """Base for risk-engine vetoes. A raised RiskError must prevent the trade."""


class RiskLimitBreached(RiskError):
    """A hard limit (daily loss, drawdown, exposure...) was hit."""


class KillSwitchActive(RiskError):
    """The kill switch is engaged; no new trades may open."""


class UnsafeMarketError(RiskError):
    """Market is in an abnormal/illiquid state unsafe for trading."""


# ── Execution layer ───────────────────────────────────────────────────────────
class ExecutionError(TradingSystemError):
    """Base for order placement / reconciliation failures."""


class OrderRejected(ExecutionError):
    """The exchange rejected the order."""


class ReconciliationError(ExecutionError):
    """Local state and exchange state disagree (orphan order, ghost position)."""
