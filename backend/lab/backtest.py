from __future__ import annotations
import math
import pandas as pd


def _wilson(successes: int, n: int, z: float = 1.96):
    if n == 0:
        return None, None
    p = successes / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    margin = z * math.sqrt((p*(1-p) + z*z/(4*n))/n) / denom
    return round(max(0, center-margin), 6), round(min(1, center+margin), 6)


def _run_segment(digits, start, end, sequence_length, stake, payout, mode):
    balance = 0.0
    peak = 0.0
    max_drawdown = 0.0
    wins = losses = 0
    trades = []
    i = max(start, sequence_length)
    while i < end:
        history = digits[i-sequence_length:i]
        if len(history) == sequence_length and (all(d % 2 == 0 for d in history) or all(d % 2 == 1 for d in history)):
            previous_parity = history[-1] % 2
            target = 1 - previous_parity if mode == "reverse" else previous_parity
            actual = digits[i] % 2
            won = actual == target
            pnl = stake * payout if won else -stake
            balance += pnl
            peak = max(peak, balance)
            max_drawdown = max(max_drawdown, peak - balance)
            wins += int(won)
            losses += int(not won)
            trades.append({
                "tick_index": i,
                "sequence": "".join(str(d) for d in history),
                "target": "even" if target == 0 else "odd",
                "actual": "even" if actual == 0 else "odd",
                "result": "win" if won else "loss",
                "pnl": round(pnl, 8),
                "cumulative_pnl": round(balance, 8),
            })
        i += 1
    n = wins + losses
    low, high = _wilson(wins, n)
    return {
        "trades": n, "wins": wins, "losses": losses,
        "win_rate": round(wins/n, 6) if n else None,
        "wilson_95_ci": [low, high] if n else None,
        "pnl": round(balance, 8),
        "profit_factor": round(sum(t["pnl"] for t in trades if t["pnl"] > 0) / abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)), 6)
            if any(t["pnl"] < 0 for t in trades) else (None if not any(t["pnl"] > 0 for t in trades) else "infinite"),
        "max_drawdown": round(max_drawdown, 8),
        "max_losing_streak": _max_losing_streak(trades),
        "trade_log": trades,
    }


def _max_losing_streak(trades):
    current = maximum = 0
    for trade in trades:
        current = current + 1 if trade["result"] == "loss" else 0
        maximum = max(maximum, current)
    return maximum


def backtest_parity(df: pd.DataFrame, sequence_length=4, stake=1.0, payout=0.9, mode="reverse") -> dict:
    digits = df["digit"].astype(int).tolist()
    n = len(digits)
    if n < max(10, sequence_length + 2):
        raise ValueError("Histórico demasiado curto para esta configuração.")
    a, b = int(n * .6), int(n * .8)
    # Each split is evaluated independently, with no overlap into the future.
    segments = {
        "train_60_percent": _run_segment(digits, 0, a, sequence_length, stake, payout, mode),
        "validation_20_percent": _run_segment(digits, a, b, sequence_length, stake, payout, mode),
        "test_20_percent": _run_segment(digits, b, n, sequence_length, stake, payout, mode),
        "full_sample": _run_segment(digits, 0, n, sequence_length, stake, payout, mode),
    }
    return {
        "configuration": {
            "sequence_length": sequence_length, "stake": stake, "assumed_payout": payout,
            "mode": mode, "mode_description": "apostar na paridade oposta" if mode == "reverse" else "apostar na mesma paridade",
            "ticks": n, "split_indices": {"train_end": a, "validation_end": b, "total": n},
        },
        "segments": segments,
        "warning": "Payout simplificado introduzido pelo utilizador; não representa necessariamente a liquidação real da Deriv. Backtest não é previsão nem garantia."
    }
