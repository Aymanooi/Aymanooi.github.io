"""Phase 2 tests — OHLCV types + data validation/quality scoring."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ohlcv import Candle, build_batch, timeframe_to_ms      # noqa: E402
from data.validation import validate                             # noqa: E402

STEP = 60_000  # 1m


def _rows(n, start=1_000_000_000_000, base=100.0, step=STEP, vol=10.0):
    return [[start + i * step, base, base + 1, base - 1, base, vol] for i in range(n)]


def test_timeframe_parsing():
    assert timeframe_to_ms("1m") == 60_000
    assert timeframe_to_ms("1H") == 3_600_000
    with pytest.raises(ValueError):
        timeframe_to_ms("3x")


def test_candle_rejects_inconsistent_ohlc():
    with pytest.raises(ValueError):
        Candle(0, 100, 99, 98, 100, 1)   # high < close → invalid


def test_clean_batch_scores_high():
    b = build_batch("BTC", "1m", _rows(100))
    r = validate(b, now_ms=b.candles[-1].ts)   # fresh
    assert r.quality.quality_score >= 0.99
    assert r.quality.coverage_score == pytest.approx(1.0)
    assert r.n_gaps == 0 and r.n_duplicates == 0


def test_gaps_reduce_coverage():
    rows = _rows(50)
    del rows[20:30]                            # remove 10 candles → a gap
    b = build_batch("BTC", "1m", rows)
    r = validate(b, now_ms=b.candles[-1].ts)
    assert r.n_gaps == 10
    assert r.quality.coverage_score < 0.85     # coverage drops


def test_duplicates_dropped_and_penalised():
    rows = _rows(20) + _rows(5)                 # 5 duplicate timestamps
    b = build_batch("BTC", "1m", rows)
    r = validate(b, now_ms=b.candles[-1].ts)
    assert r.n_duplicates == 5
    assert r.quality.quality_score < 1.0


def test_outlier_jump_detected():
    rows = _rows(30)
    rows[15][4] = 200.0                          # 100 → 200 close = +100% jump
    rows[15][2] = 200.0
    b = build_batch("BTC", "1m", rows)
    r = validate(b, now_ms=b.candles[-1].ts)
    assert r.n_outliers >= 1
    assert r.quality.quality_score < 1.0


def test_stale_data_flagged_by_freshness():
    b = build_batch("BTC", "1m", _rows(10))
    # pretend "now" is 1 hour after the last candle
    r = validate(b, now_ms=b.candles[-1].ts + 3_600_000)
    assert r.quality.freshness_seconds == pytest.approx(3600, abs=1)
    assert not r.quality.is_tradeable(0.8, 0.8, max_freshness_seconds=120)
