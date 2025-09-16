import sys
from pathlib import Path
from typing import Dict

import pandas as pd
import pytest


# Ensure `src/` is on sys.path so `api` and the package are importable.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from api.serving_constants import CATEGORICAL_FEATURES as SERVING_CATS  # noqa: E402
from api.serving_constants import NUMERICAL_FEATURES as SERVING_NUMS  # noqa: E402
from bank_customer_churn_prediction_pipeline.constants import (  # noqa: E402
    DROPPED_COLS,
    TARGET,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
)


@pytest.fixture
def sample_record_valid() -> Dict[str, object]:
    rec: Dict[str, object] = {}
    for c in SERVING_CATS:
        rec[c] = "A"
    for n in SERVING_NUMS:
        rec[n] = 1
    return rec


@pytest.fixture
def sample_df() -> pd.DataFrame:
    # Build a small, balanced dataset for stratification tests
    rows = []
    cols = DROPPED_COLS + CATEGORICAL_FEATURES + NUMERICAL_FEATURES + [TARGET]
    # 100 rows, 50 positives/50 negatives
    for i in range(100):
        row = {c: 0 for c in cols}
        # Fill dropped columns with simple values
        row["RowNumber"] = i + 1
        row["CustomerId"] = 100000 + i
        row["Surname"] = f"S{i}"
        row["Complain"] = 0
        # Categorical
        for c in CATEGORICAL_FEATURES:
            row[c] = "A" if i % 2 == 0 else "B"
        # Numerical
        for n in NUMERICAL_FEATURES:
            row[n] = float(i)
        # Target alternating 0/1
        row[TARGET] = 1 if i % 2 == 0 else 0
        rows.append(row)
    return pd.DataFrame(rows)[cols]


@pytest.fixture
def tmp_csv_path(tmp_path, sample_df) -> str:
    p = tmp_path / "data.csv"
    sample_df.to_csv(p, index=False)
    return str(p)


@pytest.fixture
def mlflow_noop(monkeypatch):
    """Stub mlflow side-effecting APIs to no-ops for unit tests."""
    import types
    import mlflow

    class _Ctx:
        def __enter__(self):  # noqa: D401
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401
            return False

    monkeypatch.setattr(mlflow, "start_run", lambda *a, **k: _Ctx(), raising=True)
    # Top-level helpers
    for name in [
        "log_metric",
        "log_metrics",
        "log_param",
        "log_params",
        "log_figure",
        "log_input",
        "set_tag",
        "set_tags",
    ]:
        monkeypatch.setattr(mlflow, name, lambda *a, **k: None, raising=False)

    # sklearn/xgboost submodules
    if not hasattr(mlflow, "sklearn"):
        mlflow.sklearn = types.SimpleNamespace()
    monkeypatch.setattr(
        mlflow.sklearn, "log_model", lambda *a, **k: None, raising=False
    )

    if not hasattr(mlflow, "xgboost"):
        mlflow.xgboost = types.SimpleNamespace()
    monkeypatch.setattr(
        mlflow.xgboost, "log_model", lambda *a, **k: None, raising=False
    )

    # data submodule for dataset logging
    if not hasattr(mlflow, "data"):
        mlflow.data = types.SimpleNamespace()
    monkeypatch.setattr(
        mlflow.data, "from_numpy", lambda *a, **k: object(), raising=False
    )
