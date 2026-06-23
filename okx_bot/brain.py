"""
Adaptive Learning Brain
- Online logistic-regression that learns from past trade outcomes
- Adjusts indicator weights based on what actually worked
- Kelly criterion for risk-aware position sizing
- Persists learned state to brain_memory.json

This is a REAL self-improving layer — but note: no model can predict
markets with certainty. It improves edge over time; it does not guarantee profit.
"""
import os
import json
import math
from datetime import datetime, timezone

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "brain_memory.json")

# Feature keys produced by strategy.analyze() -> details
FEATURE_KEYS = ["EMA", "RSI", "MACD", "BB", "Stoch", "Volume", "Pattern", "HTF_1h"]

DEFAULT_MEMORY = {
    "weights": {k: 1.0 for k in FEATURE_KEYS},   # learned multipliers
    "bias": 0.0,
    "trades": [],          # closed-trade history for learning
    "wins": 0,
    "losses": 0,
    "lr": 0.05,            # learning rate
    "updated": None,
}


def load_memory():
    try:
        with open(MEMORY_FILE) as f:
            m = json.load(f)
            for k in DEFAULT_MEMORY:
                m.setdefault(k, DEFAULT_MEMORY[k])
            for fk in FEATURE_KEYS:
                m["weights"].setdefault(fk, 1.0)
            return m
    except Exception:
        return json.loads(json.dumps(DEFAULT_MEMORY))


def save_memory(m):
    m["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(MEMORY_FILE, "w") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)


def _sigmoid(x):
    x = max(-30, min(30, x))
    return 1 / (1 + math.exp(-x))


def adjusted_score(details, memory):
    """
    Re-weight the raw indicator contributions using learned weights.
    Returns adjusted total score (-100..100) and win-probability estimate.
    """
    w = memory["weights"]
    raw = 0.0
    for k in FEATURE_KEYS:
        contrib = details.get(k, 0)
        raw += contrib * w.get(k, 1.0)

    # Normalise to a probability via logistic on scaled score
    z = raw / 40.0 + memory.get("bias", 0.0)
    prob_up = _sigmoid(z)
    adj = max(-100, min(100, int(raw)))
    return adj, prob_up


def kelly_fraction(win_rate, rr=3.0, cap=0.20, half=True):
    """
    Kelly = W - (1-W)/RR.
    rr   = reward:risk (TP/SL = 3.0/1.0 = 3).
    half = True → half-Kelly (safer), False → full Kelly (turbo mode).
    Returns capital fraction to risk per trade.
    """
    if win_rate <= 0:
        return 0.05
    k = win_rate - (1 - win_rate) / rr
    k = max(0.0, k)
    if half:
        k *= 0.5
    return max(0.05, min(cap, k))


def symbol_win_rate(memory, inst_id, min_trades=5):
    """Return per-symbol WR once we have enough data, else None (still exploring)."""
    sym = [t for t in memory.get("trades", [])
           if t.get("instId") == inst_id and t.get("status") in ("win", "loss")]
    if len(sym) < min_trades:
        return None
    return sum(1 for t in sym if t["status"] == "win") / len(sym)


def should_trade_symbol(memory, inst_id, rr=3.0, min_trades=5):
    """
    Return True if this symbol has positive Kelly (WR > breakeven).
    Returns True also when we don't have enough data yet (still learning).
    """
    wr = symbol_win_rate(memory, inst_id, min_trades)
    if wr is None:
        return True   # not enough data — keep exploring
    return wr > (1 / (1 + rr))   # breakeven WR = 25%


COOLDOWN_HOURS = 4

def mark_exited(memory, inst_id):
    """Record that a position on inst_id was just closed — starts cooldown timer."""
    if "exited" not in memory:
        memory["exited"] = {}
    memory["exited"][inst_id] = datetime.now(timezone.utc).isoformat()

def can_reenter(memory, inst_id, cooldown_hours=COOLDOWN_HOURS):
    """True if cooldown has passed (or symbol never exited before)."""
    exited = memory.get("exited", {})
    if inst_id not in exited:
        return True
    try:
        exited_at = datetime.fromisoformat(exited[inst_id])
        elapsed_h = (datetime.now(timezone.utc) - exited_at).total_seconds() / 3600
        return elapsed_h >= cooldown_hours
    except Exception:
        return True


def open_instruments(memory):
    """Set of instIds the brain believes are still open (recorded but not yet learned)."""
    return {t["instId"] for t in memory.get("trades", []) if t.get("status") == "open"}


def record_open(memory, inst_id, signal, details, entry_price, score):
    """Log an opened trade so we can learn from it when it closes."""
    memory["trades"].append({
        "instId": inst_id,
        "signal": signal,
        "features": {k: details.get(k, 0) for k in FEATURE_KEYS},
        "entry": entry_price,
        "score": score,
        "status": "open",
        "opened": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    })
    memory["trades"] = memory["trades"][-200:]


def learn_from_closed(memory, inst_id, exit_price):
    """
    Find the open trade for inst_id, compute win/loss, and update weights
    via gradient step on logistic loss.
    """
    for t in reversed(memory["trades"]):
        if t["instId"] == inst_id and t["status"] == "open":
            entry = t["entry"]
            if t["signal"] == "buy":
                pnl = exit_price - entry
            else:
                pnl = entry - exit_price
            won = 1 if pnl > 0 else 0
            t["status"] = "win" if won else "loss"
            t["exit"] = exit_price

            if won:
                memory["wins"] += 1
            else:
                memory["losses"] += 1

            # Gradient step: predicted prob vs actual outcome
            raw = sum(t["features"].get(k, 0) * memory["weights"].get(k, 1.0)
                      for k in FEATURE_KEYS)
            z = raw / 40.0 + memory["bias"]
            pred = _sigmoid(z)
            error = won - pred
            lr = memory.get("lr", 0.05)

            for k in FEATURE_KEYS:
                grad = error * (t["features"].get(k, 0) / 40.0)
                memory["weights"][k] += lr * grad
                # keep weights in sane range
                memory["weights"][k] = max(0.1, min(3.0, memory["weights"][k]))
            memory["bias"] += lr * error * 0.1
            return won
    return None


def current_win_rate(memory):
    total = memory["wins"] + memory["losses"]
    if total < 5:
        return 0.5   # default until enough data
    return memory["wins"] / total


def stats(memory):
    total = memory["wins"] + memory["losses"]
    wr = current_win_rate(memory)
    return {
        "wins": memory["wins"],
        "losses": memory["losses"],
        "total_closed": total,
        "win_rate": round(wr * 100, 1),
        "weights": {k: round(v, 3) for k, v in memory["weights"].items()},
        "kelly": round(kelly_fraction(wr) * 100, 1),
        "updated": memory.get("updated"),
    }
