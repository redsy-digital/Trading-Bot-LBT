import json
from datetime import datetime, timezone
from io import BytesIO, StringIO
import pandas as pd
import numpy as np

def _first(d, names, default=None):
    for name in names:
        if name in d and d[name] is not None:
            return d[name]
    return default

def _normalise_records(records, symbol=None):
    rows = []
    for item in records:
        if not isinstance(item, dict):
            continue
        quote = _first(item, ["quote", "price", "close", "value"])
        epoch = _first(item, ["epoch", "timestamp", "time", "datetime"])
        sym = _first(item, ["symbol", "underlying", "market"], symbol)
        pip = _first(item, ["pip_size", "pipSize", "precision"])
        if quote is None:
            continue
        try:
            q = float(quote)
            ts = float(epoch) if epoch is not None else np.nan
            pip_size = int(pip) if pip is not None else None
        except (ValueError, TypeError):
            continue
        rows.append({"epoch": ts, "datetime_utc": datetime.fromtimestamp(ts, timezone.utc).isoformat() if np.isfinite(ts) else None,
                     "symbol": str(sym) if sym is not None else None, "quote": q, "pip_size": pip_size})
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("Não encontrei registos com quote/price válidos no ficheiro.")
    if "pip_size" not in df: df["pip_size"] = None
    df["pip_size"] = df["pip_size"].astype("Int64")
    df["digit"] = df.apply(lambda r: last_digit(r["quote"], r["pip_size"]), axis=1)
    df["delta"] = df["quote"].diff()
    df["return_pct"] = df["quote"].pct_change() * 100
    return df.reset_index(drop=True)

def last_digit(quote, pip_size=None):
    # Prefer instrument precision when provided. Decimal formatting avoids binary-float string artifacts.
    if pip_size is not None and not pd.isna(pip_size):
        decimals = max(0, min(10, int(pip_size)))
        rendered = f"{float(quote):.{decimals}f}"
    else:
        rendered = f"{float(quote):.8f}".rstrip("0").rstrip(".")
    decimals_part = rendered.partition(".")[2]
    if not decimals_part:
        return 0
    return int(decimals_part[-1])

def load_uploaded_file(uploaded):
    raw = uploaded.getvalue()
    name = getattr(uploaded, "name", "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(BytesIO(raw))
        lower_map = {str(c).lower(): c for c in df.columns}
        quote_col = next((lower_map[k] for k in ["quote","price","close","value"] if k in lower_map), None)
        time_col = next((lower_map[k] for k in ["epoch","timestamp","time","datetime"] if k in lower_map), None)
        sym_col = next((lower_map[k] for k in ["symbol","underlying","market"] if k in lower_map), None)
        pip_col = next((lower_map[k] for k in ["pip_size","pipsize","precision"] if k in lower_map), None)
        if quote_col is None: raise ValueError("CSV precisa de uma coluna quote, price, close ou value.")
        recs = []
        for _, r in df.iterrows():
            recs.append({"quote":r[quote_col], "epoch":r[time_col] if time_col else None,
                         "symbol":r[sym_col] if sym_col else None, "pip_size":r[pip_col] if pip_col else None})
        return _normalise_records(recs)
    data = json.loads(raw.decode("utf-8-sig"))
    symbol = None
    if isinstance(data, dict):
        symbol = data.get("symbol")
        if isinstance(data.get("history"), dict):
            h = data["history"]
            prices = h.get("prices", [])
            times = h.get("times", [])
            records = [{"quote":p, "epoch":times[i] if i < len(times) else None, "symbol":symbol,
                        "pip_size": data.get("pip_size")} for i,p in enumerate(prices)]
        elif isinstance(data.get("ticks"), list):
            records = data["ticks"]
        elif isinstance(data.get("data"), list):
            records = data["data"]
        elif isinstance(data.get("prices"), list):
            prices = data["prices"]; times = data.get("times", [])
            records = [{"quote":p, "epoch":times[i] if i < len(times) else None, "symbol":symbol,
                        "pip_size":data.get("pip_size")} for i,p in enumerate(prices)]
        else:
            # Handle Deriv-style envelope {"history": {"prices":...}} and a single tick.
            records = [data] if any(k in data for k in ("quote","price","close","value")) else []
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError("Formato JSON não suportado.")
    return _normalise_records(records, symbol)

def validate_ticks(df):
    df = df.copy()
    issues = []
    if df["epoch"].isna().any():
        issues.append({"Tipo":"Timestamp ausente", "Quantidade":int(df["epoch"].isna().sum()), "Detalhe":"Algumas análises temporais ficam limitadas."})
    if df["symbol"].dropna().nunique() > 1:
        issues.append({"Tipo":"Símbolos misturados", "Quantidade":int(df["symbol"].dropna().nunique()), "Detalhe":"Não combines mercados diferentes numa única série."})
    dup = int(df.duplicated(subset=["epoch","quote","symbol"], keep="first").sum())
    if dup:
        issues.append({"Tipo":"Duplicados", "Quantidade":dup, "Detalhe":"Duplicados preservados para auditoria; remove-os apenas se confirmares que são duplicados reais."})
    if df["epoch"].notna().sum() > 1:
        valid = df["epoch"].dropna()
        out = int((valid.diff().dropna() < 0).sum())
        if out:
            issues.append({"Tipo":"Ordem temporal invertida", "Quantidade":out, "Detalhe":"Os dados foram ordenados por timestamp para análise; conserva o original fora desta vista."})
            df = df.sort_values("epoch", kind="stable", na_position="last").reset_index(drop=True)
        diffs = valid.sort_values().diff().dropna()
        gaps = int((diffs > max(5, diffs.median()*3)).sum()) if len(diffs) else 0
        if gaps:
            issues.append({"Tipo":"Possíveis lacunas temporais", "Quantidade":gaps, "Detalhe":"Intervalos longos podem indicar ticks ausentes ou pausas."})
    df["delta"] = df["quote"].diff()
    df["return_pct"] = df["quote"].pct_change() * 100
    return df, pd.DataFrame(issues, columns=["Tipo","Quantidade","Detalhe"])

def export_ticks_json(df, source="importado"):
    payload = {"schema":"x-one-research-lab.ticks.v1",
               "metadata":{"symbol":str(df["symbol"].dropna().iloc[0]) if df["symbol"].notna().any() else None,
                           "source":source, "exported_at_utc":datetime.now(timezone.utc).isoformat(),
                           "tick_count":int(len(df)), "notes":"Dados normalizados; não altera a cotação original."},
               "ticks":[{"epoch":None if pd.isna(r.epoch) else float(r.epoch),
                         "datetime_utc":r.datetime_utc if pd.notna(r.datetime_utc) else None,
                         "symbol":r.symbol if pd.notna(r.symbol) else None,
                         "quote":float(r.quote),
                         "pip_size":None if pd.isna(r.pip_size) else int(r.pip_size),
                         "digit":int(r.digit)} for r in df.itertuples()]}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

def export_ticks_csv(df):
    cols = ["epoch","datetime_utc","symbol","quote","pip_size","digit","delta","return_pct"]
    return df[[c for c in cols if c in df.columns]].to_csv(index=False).encode("utf-8")
