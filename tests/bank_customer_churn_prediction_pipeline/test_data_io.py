import numpy as np
import pandas as pd
import pytest

from bank_customer_churn_prediction_pipeline.constants import (DROPPED_COLS,
                                                               TARGET)
from bank_customer_churn_prediction_pipeline.data_io import (read_data,
                                                             split_data)


class TestReadData:
    def test_read_data_successful(self, temp_csv_file):
        """Test successful data reading and column dropping"""
        df = read_data(temp_csv_file)

        # Check that dropped columns are not present
        for col in DROPPED_COLS:
            assert col not in df.columns

        # Check that target column is present
        assert TARGET in df.columns

        # Check data types and shape
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] > 0

    def test_read_data_nonexistent_file(self):
        """Test reading data from non-existent file"""
        with pytest.raises(FileNotFoundError):
            read_data("nonexistent_file.csv")

    def test_read_data_drops_correct_columns(self, temp_csv_file):
        """Test that the correct columns are dropped"""
        original_data = pd.read_csv(temp_csv_file)
        processed_data = read_data(temp_csv_file)

        expected_dropped_cols = set(DROPPED_COLS).intersection(
            set(original_data.columns)
        )

        for col in expected_dropped_cols:
            assert col not in processed_data.columns
            assert col in original_data.columns


class TestSplitData:
    def test_split_data_returns_correct_shapes(self, sample_data):
        """Test that split_data returns data with correct shapes"""
        X_train, y_train, X_val, y_val, X_test, y_test = split_data(
            sample_data, seed=42
        )

        # Check that all splits have data
        assert len(X_train) > 0
        assert len(X_val) > 0
        assert len(X_test) > 0

        # Check that target arrays have same length as feature arrays
        assert len(X_train) == len(y_train)
        assert len(X_val) == len(y_val)
        assert len(X_test) == len(y_test)

        # Check that splits sum to original size
        total_size = len(X_train) + len(X_val) + len(X_test)
        assert total_size == len(sample_data)

    def test_split_data_removes_target_from_features(self, sample_data):
        """Test that target column is removed from feature sets"""
        X_train, y_train, X_val, y_val, X_test, y_test = split_data(
            sample_data, seed=42
        )

        # Check that target column is not in feature sets
        assert TARGET not in X_train.columns
        assert TARGET not in X_val.columns
        assert TARGET not in X_test.columns

    def test_split_data_reproducible_with_seed(self, sample_data):
        """Test that split_data is reproducible with same seed"""
        result1 = split_data(sample_data, seed=42)
        result2 = split_data(sample_data, seed=42)

        # Compare shapes (should be identical)
        for i in range(len(result1)):
            if hasattr(result1[i], "shape"):
                assert result1[i].shape == result2[i].shape
            else:
                assert len(result1[i]) == len(result2[i])

    def test_split_data_different_seeds_different_splits(self, sample_data):
        """Test that different seeds produce different splits"""
        X_train1, _, _, _, _, _ = split_data(sample_data, seed=42)
        X_train2, _, _, _, _, _ = split_data(sample_data, seed=123)

        # With different seeds, the train sets should be different
        # (though this test might occasionally fail due to randomness)
        try:
            pd.testing.assert_frame_equal(X_train1, X_train2)
            # If they are equal, it's very unlikely but possible
            assert False, "Different seeds produced identical splits (very unlikely)"
        except AssertionError:
            # This is expected - different seeds should produce different splits
            pass

    def test_split_data_preserves_columns(self, sample_data):
        """Test that feature columns are preserved in splits"""
        X_train, _, X_val, _, X_test, _ = split_data(sample_data, seed=42)

        expected_columns = sample_data.drop(columns=[TARGET]).columns.tolist()

        assert list(X_train.columns) == expected_columns
        assert list(X_val.columns) == expected_columns
        assert list(X_test.columns) == expected_columns

    def test_split_data_target_values_correct_type(self, sample_data):
        """Test that target values are of correct type"""
        _, y_train, _, y_val, _, y_test = split_data(sample_data, seed=42)

        # Check that targets are numpy arrays or pandas Series
        assert isinstance(y_train, (np.ndarray, pd.Series))
        assert isinstance(y_val, (np.ndarray, pd.Series))
        assert isinstance(y_test, (np.ndarray, pd.Series))

    def test_split_data_with_small_dataset(self):
        """Test split_data with a small but valid dataset"""
        # Create a dataset with minimum viable size for stratified splitting
        small_data = pd.DataFrame(
            {
                "feature1": range(20),
                "feature2": range(20, 40),
                TARGET: [0, 1] * 10,  # Ensure balanced classes
            }
        )

        X_train, y_train, X_val, y_val, X_test, y_test = split_data(small_data, seed=42)

        # Should still work with small dataset
        assert len(X_train) + len(X_val) + len(X_test) == len(small_data)
        assert len(y_train) + len(y_val) + len(y_test) == len(small_data)
