from __future__ import annotations
import math
import numpy as np
import pandas as pd


def _safe_float(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def analyze_ticks(df: pd.DataFrame) -> dict:
    digits = df["digit"].astype(int)
    counts = digits.value_counts().reindex(range(10), fill_value=0)
    total = int(len(df))
    parity_counts = digits.map(lambda d: "even" if d % 2 == 0 else "odd").value_counts()
    changes = df["price"].diff().dropna()
    returns = df["price"].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    digit_lag_corr = _safe_float(digits.astype(float).autocorr(lag=1)) if total > 2 else None

    # Consecutive same-parity runs
    parities = digits.map(lambda d: d % 2).tolist()
    runs = []
    current = 0
    previous = None
    for parity in parities:
        current = current + 1 if parity == previous else 1
        runs.append(current)
        previous = parity

    conditional = []
    for n in range(1, min(10, total - 1) + 1):
        samples = 0
        next_even = 0
        for i in range(n, total):
            if len(set(parities[i-n:i])) == 1:
                samples += 1
                next_even += int(parities[i] == 0)
        conditional.append({
            "sequence_length": n,
            "samples": samples,
            "next_even_probability": round(next_even / samples, 6) if samples else None,
            "next_odd_probability": round((samples-next_even) / samples, 6) if samples else None,
        })

    return {
        "summary": {
            "ticks": total,
            "symbol": next((str(x) for x in df["symbol"].tolist() if x), ""),
            "first_price": _safe_float(df["price"].iloc[0]),
            "last_price": _safe_float(df["price"].iloc[-1]),
            "net_change": _safe_float(df["price"].iloc[-1] - df["price"].iloc[0]),
            "mean_absolute_change": _safe_float(changes.abs().mean()),
            "std_return_pct": _safe_float(returns.std() * 100 if len(returns) > 1 else None),
            "price_return_autocorrelation_lag1": _safe_float(returns.autocorr(lag=1) if len(returns) > 2 else None),
            "digit_autocorrelation_lag1": digit_lag_corr,
            "max_same_parity_run": max(runs) if runs else 0,
        },
        "digit_distribution": [
            {"digit": int(d), "count": int(counts[d]), "frequency": round(int(counts[d]) / total, 6)}
            for d in range(10)
        ],
        "parity_distribution": [
            {"parity": parity, "count": int(parity_counts.get(parity, 0)),
             "frequency": round(int(parity_counts.get(parity, 0)) / total, 6)}
            for parity in ("even", "odd")
        ],
        "conditional_parity": conditional,
        "notes": [
            "Frequências observadas descrevem apenas a amostra importada.",
            "Autocorrelação próxima de zero não prova independência perfeita.",
            "O dígito final depende da precisão (pip_size) do símbolo e do formato de origem."
        ]
    }
