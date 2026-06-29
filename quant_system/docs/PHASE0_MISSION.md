# Phase 0 — Mission Definition

## Problem
Build an institutional-grade, modular trading system that **survives first and
profits second**, with full testability, explainability, and risk control —
without unrealistic claims.

## Assumptions
- Exchange: OKX perpetual swaps (adapter-isolated so it can be swapped).
- Any edge is **thin and decays**; markets can move violently at any time.
- Backtests overstate live performance; out-of-sample / forward results govern.
- Capital is finite and precious; **avoiding ruin outranks maximizing return**.

## Constraints
- Secrets only via environment variables; never in code or logs.
- Every trade requires: pre-computed risk, a logical stop, acceptable data
  quality, acceptable liquidity, and a non-stressed regime — else **no trade**.
- Leverage is a capital-efficiency tool, bounded by a strict risk framework.
- Daily/weekly loss caps and a drawdown kill switch are non-negotiable.

## Risks (and mitigations)
| Risk | Mitigation |
|---|---|
| Edge decay / overfitting | walk-forward + OOS gating; reject param-fragile strategies |
| Data gaps / bad ticks | data-validation layer tags low quality → fail closed |
| Violent markets | regime detector → stressed state stands strategies down |
| Execution faults | idempotent orders, reconciliation, orphan detection |
| Over-leverage | leverage capped by liquidation-distance buffer |
| Operator/compulsion risk | hard daily loss cap + kill switch the human can't override mid-session |

## Final deliverables
A runnable system spanning: data → validation → features → regime → strategies →
risk → sizing → execution → monitoring, with backtest + walk-forward + paper +
guarded live, plus tests, docs, and an audit trail.

## Execution order
Phase 1 architecture → **Phase 2 data** → 3 features → 4 regime → 5 strategies →
6 risk engine → 8 portfolio → 9 execution → 10 backtest → 11 walk-forward →
14 monitoring → 13 paper → 17 live. Build now: the foundation + data pipeline.
**Defer:** live trading, ML adaptation, containerization — only after backtest +
paper prove a *defensible* edge.

## What was built in this step (Phase 1 foundation)
- `core/types.py` — `DataQuality`, `Signal` (with safety invariants), `Regime`, `Side`.
- `risk/limits.py` — `RiskLimits` (loss caps, leverage cap by liquidation buffer).
- `config/settings.py` — env-driven config; defaults to **paper**; secrets from env.
- `utils/exceptions.py` — typed, fail-closed exception hierarchy.
- `tests/test_foundation.py` — 8 passing tests covering the invariants above.
