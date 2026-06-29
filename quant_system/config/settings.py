"""
Environment-based configuration.

Rules (spec Phase 15):
  * Secrets come ONLY from environment variables — never hard-coded, never logged.
  * Modes are explicit; the system defaults to the *safest* mode (paper trading).
  * Loading is validated and reproducible.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum

from utils.exceptions import ConfigError, MissingCredentialError
from risk.limits import RiskLimits


class RunMode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"          # default — no real money
    LIVE = "live"


@dataclass(frozen=True)
class ExchangeCredentials:
    api_key: str
    api_secret: str
    passphrase: str
    is_demo: bool

    def redacted(self) -> dict:
        """Safe representation for logging — secrets masked."""
        mask = lambda s: (s[:3] + "***") if s else ""
        return {"api_key": mask(self.api_key), "api_secret": "***",
                "passphrase": "***", "is_demo": self.is_demo}


@dataclass(frozen=True)
class Settings:
    mode: RunMode
    exchange: str
    risk: RiskLimits = field(default_factory=RiskLimits)
    timeframe: str = "1m"
    htf_timeframes: tuple = ("5m", "15m", "1H")

    @staticmethod
    def _env(name: str, default: str | None = None) -> str:
        val = os.environ.get(name, default)
        if val is None:
            raise ConfigError(f"missing required env var: {name}")
        return val

    @classmethod
    def from_env(cls) -> "Settings":
        mode = RunMode(cls._env("QS_MODE", RunMode.PAPER.value).strip().lower())
        return cls(mode=mode, exchange=cls._env("QS_EXCHANGE", "okx"))

    @staticmethod
    def load_credentials() -> ExchangeCredentials:
        """Load API secrets from env. Required only for paper(demo)/live."""
        key = os.environ.get("OKX_API_KEY", "").strip()
        secret = os.environ.get("OKX_API_SECRET", "").strip()
        phrase = os.environ.get("OKX_PASSPHRASE", "").strip()
        is_demo = os.environ.get("OKX_IS_DEMO", "1").strip() != "0"
        if not (key and secret and phrase):
            raise MissingCredentialError(
                "OKX_API_KEY / OKX_API_SECRET / OKX_PASSPHRASE must be set in env")
        return ExchangeCredentials(key, secret, phrase, is_demo)
