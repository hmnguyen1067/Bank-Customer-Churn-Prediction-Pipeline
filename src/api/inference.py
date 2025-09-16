from typing import Any, Dict, Iterable, List
import pandas as pd
import numpy as np
import xgboost as xgb

from .serving_constants import CATEGORICAL_FEATURES, NUMERICAL_FEATURES
from .loader import ModelBundle


FEATURE_ORDER: List[str] = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)


class ValidationError(Exception):
    pass


def validate_and_frame(records: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    records = list(records)
    if not records:
        raise ValidationError("Instances must contain at least one record")

    required = set(FEATURE_ORDER)
    framed_rows: List[List[Any]] = []

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise ValidationError(f"Record at index {idx} is not an object")

        missing = required.difference(rec.keys())
        if missing:
            raise ValidationError(
                f"Record {idx} missing required keys: {sorted(missing)}"
            )

        # Keep only known keys and in the expected order
        row = [rec.get(col) for col in FEATURE_ORDER]
        framed_rows.append(row)

    df = pd.DataFrame(framed_rows, columns=FEATURE_ORDER)

    # Basic type coercion for numeric columns
    for col in NUMERICAL_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            raise ValidationError(
                f"Column '{col}' contains non-numeric or null values after coercion"
            )

    return df


def make_predictions(model, X_test: pd.DataFrame, preprocessor) -> np.ndarray:
    X_test = preprocessor.transform(X_test)
    preds = model.predict(xgb.DMatrix(X_test))
    return np.clip(np.rint(preds), 0, 1).astype(int)


def predict_labels(bundle: ModelBundle, df) -> list[int]:
    preds = make_predictions(bundle.model, df, bundle.preprocessor)
    return list(preds)
