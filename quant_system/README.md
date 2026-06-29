# Quant System — Survival-First Trading Framework

A modular, testable, **risk-first** trading framework. Built phase by phase to
production quality. It does **not** promise to turn small capital into wealth; it
is engineered to *survive adverse conditions* and to trade **only when an edge is
defensible**, measuring everything along the way.

## Prime directives
1. Survival first · 2. Risk first · 3. Data quality first · 4. Testing first ·
5. Discipline first — **then** growth.

## Hard prohibitions
No martingale, no aggressive grid averaging, no all-in, no loss-doubling, no
revenge trading, no blind leverage, no untestable strategies, no unexplainable
decisions, no daily/weekly risk-limit overrides.

## Status (phase-by-phase build)
- [x] **Phase 0** — Mission definition (`docs/PHASE0_MISSION.md`)
- [x] **Phase 1** — Architecture + tested foundation
      (`core/`, `risk/limits.py`, `config/`, `utils/`, `tests/`)
- [ ] **Phase 2** — Data ingestion & validation pipeline  ← next
- [ ] Phases 3–20 — features, regime, strategies, risk engine, execution,
      backtesting, walk-forward, monitoring, …

## Layout
```
config/   settings, risk parameters (env-driven, no secrets in code)
core/     shared domain types (DataQuality, Signal, Regime, Side)
data/     ingestion + validation (Phase 2)
features/ feature engineering (Phase 3)
regime/   market-regime detection (Phase 4)
strategies/ explainable strategy engine (Phase 5)
risk/     risk limits + risk engine — the system's guardian (Phase 6)
portfolio/ sizing & allocation (Phase 8)
execution/ order lifecycle + exchange adapter (Phase 9)
backtesting/ event-driven, fee/slippage-aware (Phase 10)
paper_trading/ live/paper parity (Phase 13/16)
live_trading/  guarded live loop (Phase 17)
monitoring/ alerts/ logging/ — observability (Phase 14)
tests/    unit + integration + parity tests
docs/     design decisions & runbook
```

## Run tests
```bash
cd quant_system && python -m pytest -q
```
