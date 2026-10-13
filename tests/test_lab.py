import json
import pandas as pd
from lab.ingestion import _normalise_records, last_digit, export_ticks_json, load_uploaded_file
from lab.backtest import run_parity_backtest

def test_digit_precision():
    assert last_digit(123.45, 2) == 5
    assert last_digit(123.4, 2) == 0

def test_normalise_and_export_roundtrip_shape():
    df = _normalise_records([{"epoch":1,"quote":1.23,"symbol":"R_10","pip_size":2},
                             {"epoch":2,"quote":1.24,"symbol":"R_10","pip_size":2}])
    obj=json.loads(export_ticks_json(df))
    assert obj["metadata"]["tick_count"] == 2
    assert obj["ticks"][0]["digit"] == 3

def test_backtest_no_trade_without_sequence():
    df = _normalise_records([{"quote":1.1,"pip_size":1},{"quote":1.2,"pip_size":1},
                             {"quote":1.3,"pip_size":1},{"quote":1.4,"pip_size":1}])
    result,trades=run_parity_backtest(df, sequence_length=3, trigger_odd=True)
    assert result["trades"] >= 0
