"""
Phase 1 foundation tests — types, risk limits, config, signal invariants.

Run: cd quant_system && python -m pytest -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.types import DataQuality, Signal, Side, Regime          # noqa: E402
from risk.limits import RiskLimits                                # noqa: E402
from config.settings import Settings, RunMode                     # noqa: E402
from utils.exceptions import ConfigError, MissingCredentialError  # noqa: E402


# ── DataQuality ───────────────────────────────────────────────────────────────
def test_data_quality_validates_ranges():
    with pytest.raises(ValueError):
        DataQuality("okx", 1.0, 1.2, 0.9, 5.0, 0.9)   # quality_score > 1

def test_data_quality_tradeable_gate():
    good = DataQuality("okx", 10, 0.95, 0.95, 5.0, 0.99)
    stale = DataQuality("okx", 600, 0.95, 0.95, 5.0, 0.99)
    assert good.is_tradeable(0.8, 0.8, 120)
    assert not stale.is_tradeable(0.8, 0.8, 120)      # too old → fail closed


# ── Signal invariants ─────────────────────────────────────────────────────────
def test_signal_rejects_wrong_side_stop():
    with pytest.raises(ValueError):
        Signal("BTC", Side.BUY, "trend", 0.7, Regime.TRENDING,
               entry_ref_price=100, stop_loss_price=101,   # stop above entry → bad
               take_profit_price=103, reason="x", invalidation="y")

def test_signal_reward_risk_and_stop_distance():
    s = Signal("BTC", Side.BUY, "trend", 0.7, Regime.TRENDING,
               entry_ref_price=100, stop_loss_price=99,
               take_profit_price=103, reason="x", invalidation="y")
    assert s.stop_distance_pct == pytest.approx(0.01)
    assert s.reward_risk == pytest.approx(3.0)


# ── RiskLimits ────────────────────────────────────────────────────────────────
def test_risk_limits_reject_insane_per_trade_risk():
    with pytest.raises(ValueError):
        RiskLimits(max_risk_per_trade_pct=0.5)            # 50% per trade → reject

def test_leverage_capped_by_liquidation_buffer():
    r = RiskLimits(max_leverage=50, liquidation_buffer_pct=0.06)
    # buffer cap = 1/0.06 ≈ 16.7 → leverage capped well below the 50 ceiling
    assert r.max_leverage_for_stop(0.005) <= 17


# ── Settings ──────────────────────────────────────────────────────────────────
def test_settings_defaults_to_paper(monkeypatch):
    monkeypatch.delenv("QS_MODE", raising=False)
    s = Settings.from_env()
    assert s.mode is RunMode.PAPER          # safest default

def test_missing_credentials_raise(monkeypatch):
    for k in ("OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSPHRASE"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(MissingCredentialError):
        Settings.load_credentials()
