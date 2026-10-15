from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.lab.ingestion import normalize_ticks
from backend.lab.analysis import analyze_ticks
from backend.lab.backtest import backtest_parity

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="X-One Research Lab API", version="1.1.0")


class AnalyzeRequest(BaseModel):
    ticks: list[dict[str, Any]] = Field(min_length=2, max_length=5000)


class BacktestRequest(BaseModel):
    ticks: list[dict[str, Any]] = Field(min_length=10, max_length=5000)
    sequence_length: int = Field(default=4, ge=1, le=30)
    stake: float = Field(default=1.0, gt=0, le=1_000_000)
    payout: float = Field(default=0.9, ge=0, le=100)
    mode: str = Field(default="reverse", pattern="^(reverse|same)$")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/styles.css")
def styles():
    return FileResponse(BASE_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(BASE_DIR / "app.js", media_type="application/javascript")


@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "service": "X-One Research Lab", "version": "1.1.0"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    try:
        df = normalize_ticks(request.ticks)
        if len(df) < 2:
            raise ValueError("São necessários pelo menos 2 ticks válidos.")
        return analyze_ticks(df)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/backtest")
def backtest(request: BacktestRequest):
    try:
        df = normalize_ticks(request.ticks)
        if len(df) < 10:
            raise ValueError("São necessários pelo menos 10 ticks válidos para o backtest.")
        return backtest_parity(
            df,
            sequence_length=request.sequence_length,
            stake=request.stake,
            payout=request.payout,
            mode=request.mode,
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/normalize")
def normalize(request: AnalyzeRequest):
    try:
        df = normalize_ticks(request.ticks)
        return {"count": len(df), "ticks": df.where(pd.notna(df), None).to_dict(orient="records")}
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
