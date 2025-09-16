from bank_customer_churn_prediction_pipeline.data_io import read_data, split_data
from bank_customer_churn_prediction_pipeline.constants import (
    DROPPED_COLS,
    TARGET,
)


def test_read_data_drops_columns_and_keeps_target(tmp_csv_path):
    out = read_data(tmp_csv_path)
    for c in DROPPED_COLS:
        assert c not in out.columns
    assert TARGET in out.columns


def test_split_data_shapes_and_stratification(sample_df):
    df = sample_df.drop(columns=DROPPED_COLS)
    X_train, y_train, X_val, y_val, X_test, y_test = split_data(df, seed=42)

    # No target in feature frames
    for X in (X_train, X_val, X_test):
        assert TARGET not in X.columns

    # Expected sizes for 100 rows: 80 train, 10 val, 10 test
    assert len(y_train) == 80
    assert len(y_val) == 10
    assert len(y_test) == 10

    # Stratified split should keep class balance (50/50 -> sums below)
    # Our sample_df has 1 for even indices -> 40 ones in train, 5 in val/test
    assert int(y_train.sum()) == 40
    assert int(y_val.sum()) == 5
    assert int(y_test.sum()) == 5
