from typing import Tuple

import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .constants import (CATEGORICAL_FEATURES, NUMERICAL_FEATURES,
                        PREPROCESSOR_MODEL_NAME)


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "oh",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("scaler", StandardScaler(), NUMERICAL_FEATURES),
        ]
    )


def fit_transform_preprocessor(
    preprocessor: ColumnTransformer,
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray]:
    X_train = preprocessor.fit_transform(X_train)
    X_val = preprocessor.transform(X_val)
    return X_train, X_val


def preprocess_data(
    X_train: pd.DataFrame, X_val: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Returns transformed datasets and the fitted preprocessor; also logs preprocessor to MLflow.
    """
    preprocessor = build_preprocessor()
    X_train, X_val = fit_transform_preprocessor(preprocessor, X_train, X_val)
    with mlflow.start_run(nested=True):
        mlflow.sklearn.log_model(
            sk_model=preprocessor,
            name="preprocessor",
            registered_model_name=PREPROCESSOR_MODEL_NAME,
        )
        feature_names = preprocessor.get_feature_names_out()
    return X_train, X_val, feature_names
