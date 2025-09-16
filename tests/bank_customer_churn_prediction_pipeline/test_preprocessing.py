import numpy as np

from bank_customer_churn_prediction_pipeline.preprocessing import (
    build_preprocessor,
    fit_transform_preprocessor,
    preprocess_data,
)
from bank_customer_churn_prediction_pipeline.constants import (
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET,
)


def test_build_preprocessor_structure():
    pp = build_preprocessor()
    names = [t[0] for t in pp.transformers]
    assert "oh" in names and "scaler" in names
    # Verify assigned columns
    cols_map = {name: cols for name, _, cols in pp.transformers}
    assert list(cols_map["oh"]) == list(CATEGORICAL_FEATURES)
    assert list(cols_map["scaler"]) == list(NUMERICAL_FEATURES)


def test_fit_transform_preprocessor_shapes(sample_df):
    X = sample_df.drop(columns=[TARGET])
    X_train = X.iloc[:20].copy()
    X_val = X.iloc[20:30].copy()
    pp = build_preprocessor()
    Xtr_tf, Xval_tf = fit_transform_preprocessor(pp, X_train, X_val)
    assert isinstance(Xtr_tf, np.ndarray) and isinstance(Xval_tf, np.ndarray)
    assert Xtr_tf.shape[0] == len(X_train)
    assert Xval_tf.shape[0] == len(X_val)

    assert Xtr_tf.shape[1] == Xval_tf.shape[1]
    assert Xtr_tf.shape[1] > 0


def test_preprocess_data_logs_model_and_returns_names(sample_df, mlflow_noop):
    X = sample_df.drop(columns=[TARGET])
    X_train = X.iloc[:20].copy()
    X_val = X.iloc[20:40].copy()
    Xtr_tf, Xval_tf, feat_names = preprocess_data(X_train, X_val)
    assert isinstance(Xtr_tf, np.ndarray) and isinstance(Xval_tf, np.ndarray)
    assert len(feat_names) == Xtr_tf.shape[1] == Xval_tf.shape[1]
    assert all(isinstance(n, str) for n in feat_names)
