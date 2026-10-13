from __future__ import annotations
from typing import Any
import math
import pandas as pd


def _number(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def normalize_ticks(payload: Any) -> pd.DataFrame:
    """Normalize tick rows. Accepts rows or Deriv history-like data."""
    if isinstance(payload, dict):
        if "history" in payload and isinstance(payload["history"], dict):
            history = payload["history"]
            prices = history.get("prices", [])
            times = history.get("times", [])
            payload = [
                {"price": p, "epoch": times[i] if i < len(times) else None,
                 "symbol": payload.get("echo_req", {}).get("ticks_history")}
                for i, p in enumerate(prices)
            ]
        else:
            payload = payload.get("ticks", payload.get("data", payload.get("prices", [])))

    if not isinstance(payload, list):
        raise ValueError("O ficheiro deve conter uma lista de ticks ou um objeto com 'ticks'/'history.prices'.")

    rows: list[dict[str, Any]] = []
    for i, item in enumerate(payload):
        if isinstance(item, (int, float, str)):
            price = _number(item)
            row = {"price": price}
        elif isinstance(item, dict):
            row = dict(item)
            price = None
            for key in ("price", "quote", "close", "value", "tick"):
                if key in row:
                    price = _number(row[key])
                    if price is not None:
                        break
        else:
            continue
        if price is None:
            continue
        epoch = None
        for key in ("epoch", "time", "timestamp", "date"):
            if row.get(key) not in (None, ""):
                epoch = row[key]
                break
        pip_size = _number(row.get("pip_size"))
        rows.append({
            "index": i,
            "epoch": epoch,
            "symbol": row.get("symbol") or row.get("underlying") or "",
            "price": price,
            "pip_size": pip_size,
        })

    if not rows:
        raise ValueError("Não encontrei preços válidos. Confirme o formato do JSON/CSV.")
    df = pd.DataFrame(rows)
    # Infer decimal precision if pip_size wasn't provided.
    def last_digit(row):
        price = float(row["price"])
        pip_size = row["pip_size"]
        if pip_size is not None and pip_size > 0:
            decimals = max(0, min(10, int(round(-math.log10(pip_size)))))
        else:
            s = f"{price:.10f}".rstrip("0").rstrip(".")
            decimals = len(s.split(".")[1]) if "." in s else 0
        scaled = round(price * (10 ** decimals))
        return int(abs(scaled)) % 10

    df["digit"] = df.apply(last_digit, axis=1)
    df["parity"] = df["digit"].map(lambda d: "even" if d % 2 == 0 else "odd")
    df["price_change"] = df["price"].diff()
    df["return_pct"] = df["price"].pct_change().replace([float("inf"), -float("inf")], pd.NA)
    return df.reset_index(drop=True)
