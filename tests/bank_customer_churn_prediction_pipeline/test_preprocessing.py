from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer

from bank_customer_churn_prediction_pipeline.constants import (
    CATEGORICAL_FEATURES, NUMERICAL_FEATURES, PREPROCESSOR_MODEL_NAME)
from bank_customer_churn_prediction_pipeline.preprocessing import (
    build_preprocessor, fit_transform_preprocessor, preprocess_data)


class TestBuildPreprocessor:
    def test_build_preprocessor_returns_column_transformer(self):
        """Test that build_preprocessor returns a ColumnTransformer"""
        preprocessor = build_preprocessor()
        assert isinstance(preprocessor, ColumnTransformer)

    def test_build_preprocessor_has_correct_transformers(self):
        """Test that the preprocessor has the expected transformers"""
        preprocessor = build_preprocessor()

        # Check that we have 2 transformers (categorical and numerical)
        assert len(preprocessor.transformers) == 2

        # Check transformer names
        transformer_names = [t[0] for t in preprocessor.transformers]
        assert "oh" in transformer_names  # OneHotEncoder
        assert "scaler" in transformer_names  # StandardScaler

    def test_build_preprocessor_handles_correct_columns(self):
        """Test that the preprocessor targets the correct columns"""
        preprocessor = build_preprocessor()

        # Extract column assignments from transformers
        categorical_cols = None
        numerical_cols = None

        for name, transformer, columns in preprocessor.transformers:
            if name == "oh":
                categorical_cols = columns
            elif name == "scaler":
                numerical_cols = columns

        assert categorical_cols == CATEGORICAL_FEATURES
        assert numerical_cols == NUMERICAL_FEATURES


class TestFitTransformPreprocessor:
    def test_fit_transform_preprocessor_returns_arrays(self, sample_features):
        """Test that fit_transform_preprocessor returns numpy arrays"""
        preprocessor = build_preprocessor()
        X_val = sample_features.copy()

        X_train_transformed, X_val_transformed = fit_transform_preprocessor(
            preprocessor, sample_features, X_val
        )

        assert isinstance(X_train_transformed, np.ndarray)
        assert isinstance(X_val_transformed, np.ndarray)

    def test_fit_transform_preprocessor_correct_shapes(self, sample_features):
        """Test that transformed data has expected shape"""
        preprocessor = build_preprocessor()
        X_val = sample_features.copy()

        X_train_transformed, X_val_transformed = fit_transform_preprocessor(
            preprocessor, sample_features, X_val
        )

        # Should have same number of rows
        assert X_train_transformed.shape[0] == len(sample_features)
        assert X_val_transformed.shape[0] == len(X_val)

        # Should have same number of features
        assert X_train_transformed.shape[1] == X_val_transformed.shape[1]

    def test_fit_transform_preprocessor_handles_missing_values(self):
        """Test preprocessing with missing values"""
        data_with_missing = pd.DataFrame(
            {
                "Geography": ["Spain", None, "Germany"],
                "Gender": ["Female", "Male", "Male"],
                "Age": [42, 41, 44],
                "Tenure": [2, 1, 8],
                "Balance": [0.0, 83807.86, 159660.8],
                "NumOfProducts": [1, 1, 3],
                "HasCrCard": [1, 0, 1],
                "IsActiveMember": [1, 1, 0],
                "EstimatedSalary": [101348.88, None, 113931.57],
                "Satisfaction Score": [2, 3, 3],
                "Card Type": ["DIAMOND", "SILVER", "DIAMOND"],
                "Point Earned": [464, 456, 377],
                "CreditScore": [619, 608, 502],
            }
        )

        preprocessor = build_preprocessor()
        X_val = data_with_missing.copy()

        # Should handle missing values without crashing
        X_train_transformed, X_val_transformed = fit_transform_preprocessor(
            preprocessor, data_with_missing, X_val
        )

        assert isinstance(X_train_transformed, np.ndarray)
        assert isinstance(X_val_transformed, np.ndarray)


class TestPreprocessData:
    @patch("bank_customer_churn_prediction_pipeline.preprocessing.mlflow")
    def test_preprocess_data_returns_correct_types(self, mock_mlflow, sample_features):
        """Test that preprocess_data returns correct types"""
        X_val = sample_features.copy()

        X_train_transformed, X_val_transformed, feature_names = preprocess_data(
            sample_features, X_val
        )

        assert isinstance(X_train_transformed, np.ndarray)
        assert isinstance(X_val_transformed, np.ndarray)
        assert isinstance(feature_names, (list, np.ndarray))

    @patch("bank_customer_churn_prediction_pipeline.preprocessing.mlflow")
    def test_preprocess_data_logs_to_mlflow(self, mock_mlflow, sample_features):
        """Test that preprocess_data logs the preprocessor to MLflow"""
        mock_run = MagicMock()
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_run

        X_val = sample_features.copy()
        preprocess_data(sample_features, X_val)

        # Check that MLflow logging was called
        mock_mlflow.start_run.assert_called_once_with(nested=True)
        mock_mlflow.sklearn.log_model.assert_called_once()

        # Check the log_model call parameters
        call_args = mock_mlflow.sklearn.log_model.call_args
        assert call_args[1]["name"] == "preprocessor"
        assert call_args[1]["registered_model_name"] == PREPROCESSOR_MODEL_NAME

    @patch("bank_customer_churn_prediction_pipeline.preprocessing.mlflow")
    def test_preprocess_data_feature_names(self, mock_mlflow, sample_features):
        """Test that feature names are extracted correctly"""
        X_val = sample_features.copy()

        X_train_transformed, X_val_transformed, feature_names = preprocess_data(
            sample_features, X_val
        )

        # Feature names should be a list/array of strings
        assert len(feature_names) > 0
        assert all(isinstance(name, str) for name in feature_names)

    @patch("bank_customer_churn_prediction_pipeline.preprocessing.mlflow")
    def test_preprocess_data_consistent_shapes(self, mock_mlflow, sample_features):
        """Test that preprocessing produces consistent shapes"""
        X_val = sample_features.copy()

        X_train_transformed, X_val_transformed, feature_names = preprocess_data(
            sample_features, X_val
        )

        # Number of features should match feature names
        assert X_train_transformed.shape[1] == len(feature_names)
        assert X_val_transformed.shape[1] == len(feature_names)

        # Number of samples should be preserved
        assert X_train_transformed.shape[0] == len(sample_features)
        assert X_val_transformed.shape[0] == len(X_val)

    @patch("bank_customer_churn_prediction_pipeline.preprocessing.mlflow")
    def test_preprocess_data_with_different_val_size(
        self, mock_mlflow, sample_features
    ):
        """Test preprocessing with different validation set size"""
        # Create smaller validation set
        X_val = sample_features.iloc[:2].copy()

        X_train_transformed, X_val_transformed, feature_names = preprocess_data(
            sample_features, X_val
        )

        # Shapes should reflect different input sizes
        assert X_train_transformed.shape[0] == len(sample_features)
        assert X_val_transformed.shape[0] == len(X_val)
        assert X_train_transformed.shape[1] == X_val_transformed.shape[1]

    def test_preprocess_data_integration(self, sample_features):
        """Integration test for the full preprocessing pipeline"""
        X_val = sample_features.copy()

        with patch("bank_customer_churn_prediction_pipeline.preprocessing.mlflow"):
            X_train_transformed, X_val_transformed, feature_names = preprocess_data(
                sample_features, X_val
            )

            # Verify the preprocessing worked correctly
            assert X_train_transformed.shape[1] > len(CATEGORICAL_FEATURES) + len(
                NUMERICAL_FEATURES
            )
            # (due to one-hot encoding expanding categorical features)

            # Check that all data is numeric (no strings after preprocessing)
            assert X_train_transformed.dtype in [np.float64, np.float32]
            assert X_val_transformed.dtype in [np.float64, np.float32]

            # Check for no NaN values after preprocessing
            assert not np.isnan(X_train_transformed).any()
            assert not np.isnan(X_val_transformed).any()
