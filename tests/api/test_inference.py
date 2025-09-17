from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from api.inference import (FEATURE_ORDER, ValidationError, make_predictions,
                           predict_labels, validate_and_frame)
from api.serving_constants import CATEGORICAL_FEATURES, NUMERICAL_FEATURES


class TestValidateAndFrame:
    def test_validate_and_frame_valid_data(self, sample_prediction_request):
        """Test validation with valid data"""
        df = validate_and_frame(sample_prediction_request["instances"])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == FEATURE_ORDER

    def test_validate_and_frame_empty_records(self):
        """Test validation with empty records"""
        with pytest.raises(ValidationError, match="at least one record"):
            validate_and_frame([])

    def test_validate_and_frame_missing_required_fields(self):
        """Test validation with missing required fields"""
        incomplete_record = [{"Geography": "Spain", "Gender": "Female"}]

        with pytest.raises(ValidationError, match="missing required keys"):
            validate_and_frame(incomplete_record)

    def test_validate_and_frame_non_dict_record(self):
        """Test validation with non-dictionary record"""
        invalid_records = ["not a dict"]

        with pytest.raises(ValidationError, match="not an object"):
            validate_and_frame(invalid_records)

    def test_validate_and_frame_numeric_coercion(self):
        """Test numeric type coercion"""
        records = [
            {
                "Geography": "Spain",
                "Gender": "Female",
                "Age": "42",  # String that can be converted
                "Tenure": 2,
                "Balance": "0.0",  # String that can be converted
                "NumOfProducts": 1,
                "HasCrCard": 1,
                "IsActiveMember": 1,
                "EstimatedSalary": "101348.88",  # String that can be converted
                "Satisfaction Score": 2,
                "Card Type": "DIAMOND",
                "Point Earned": "464",  # String that can be converted
                "CreditScore": 619,
            }
        ]

        df = validate_and_frame(records)

        # Check that numeric columns are properly typed
        for col in NUMERICAL_FEATURES:
            assert pd.api.types.is_numeric_dtype(df[col])

    def test_validate_and_frame_invalid_numeric_values(self):
        """Test validation with non-numeric values in numeric fields"""
        records = [
            {
                "Geography": "Spain",
                "Gender": "Female",
                "Age": "not_a_number",  # Invalid numeric value
                "Tenure": 2,
                "Balance": 0.0,
                "NumOfProducts": 1,
                "HasCrCard": 1,
                "IsActiveMember": 1,
                "EstimatedSalary": 101348.88,
                "Satisfaction Score": 2,
                "Card Type": "DIAMOND",
                "Point Earned": 464,
                "CreditScore": 619,
            }
        ]

        with pytest.raises(ValidationError, match="non-numeric or null values"):
            validate_and_frame(records)

    def test_validate_and_frame_extra_fields(self):
        """Test validation ignores extra fields not in FEATURE_ORDER"""
        records = [
            {
                "Geography": "Spain",
                "Gender": "Female",
                "Age": 42,
                "Tenure": 2,
                "Balance": 0.0,
                "NumOfProducts": 1,
                "HasCrCard": 1,
                "IsActiveMember": 1,
                "EstimatedSalary": 101348.88,
                "Satisfaction Score": 2,
                "Card Type": "DIAMOND",
                "Point Earned": 464,
                "CreditScore": 619,
                "ExtraField": "should be ignored",  # Extra field
            }
        ]

        df = validate_and_frame(records)

        # Should only contain expected columns
        assert list(df.columns) == FEATURE_ORDER
        assert "ExtraField" not in df.columns

    def test_validate_and_frame_multiple_records(self):
        """Test validation with multiple records"""
        records = [
            {
                "Geography": "Spain",
                "Gender": "Female",
                "Age": 42,
                "Tenure": 2,
                "Balance": 0.0,
                "NumOfProducts": 1,
                "HasCrCard": 1,
                "IsActiveMember": 1,
                "EstimatedSalary": 101348.88,
                "Satisfaction Score": 2,
                "Card Type": "DIAMOND",
                "Point Earned": 464,
                "CreditScore": 619,
            },
            {
                "Geography": "France",
                "Gender": "Male",
                "Age": 35,
                "Tenure": 5,
                "Balance": 50000.0,
                "NumOfProducts": 2,
                "HasCrCard": 0,
                "IsActiveMember": 0,
                "EstimatedSalary": 75000.00,
                "Satisfaction Score": 3,
                "Card Type": "SILVER",
                "Point Earned": 300,
                "CreditScore": 700,
            },
        ]

        df = validate_and_frame(records)
        assert len(df) == 2
        assert list(df.columns) == FEATURE_ORDER


class TestMakePredictions:
    def test_make_predictions_returns_integers(
        self, mock_preprocessor, mock_xgb_model, sample_features
    ):
        """Test that make_predictions returns integer predictions"""
        # Setup mock
        mock_xgb_model.predict.return_value = np.array([0.1, 0.8, 0.3])
        mock_preprocessor.transform.return_value = np.random.rand(3, 10)

        predictions = make_predictions(
            mock_xgb_model, sample_features, mock_preprocessor
        )

        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype == int
        assert all(pred in [0, 1] for pred in predictions)

    def test_make_predictions_clips_values(
        self, mock_preprocessor, mock_xgb_model, sample_features
    ):
        """Test that predictions are clipped to 0-1 range"""
        # Mock extreme prediction values
        mock_xgb_model.predict.return_value = np.array([-0.5, 1.5, 0.5])
        mock_preprocessor.transform.return_value = np.random.rand(3, 10)

        predictions = make_predictions(
            mock_xgb_model, sample_features, mock_preprocessor
        )

        # Should be clipped to [0, 1]
        assert all(pred in [0, 1] for pred in predictions)

    @patch("api.inference.xgb.DMatrix")
    def test_make_predictions_uses_xgb_dmatrix(
        self, mock_dmatrix, mock_preprocessor, mock_xgb_model, sample_features
    ):
        """Test that make_predictions uses XGBoost DMatrix"""
        mock_preprocessor.transform.return_value = np.random.rand(3, 10)
        mock_xgb_model.predict.return_value = np.array([0.1, 0.8, 0.3])

        make_predictions(mock_xgb_model, sample_features, mock_preprocessor)

        # Should create DMatrix for XGBoost prediction
        mock_dmatrix.assert_called_once()


class TestPredictLabels:
    def test_predict_labels_returns_list(self, mock_model_bundle, sample_features):
        """Test that predict_labels returns a list of integers"""
        predictions = predict_labels(mock_model_bundle, sample_features)

        assert isinstance(predictions, list)
        assert all(isinstance(pred, int) for pred in predictions)
        assert all(pred in [0, 1] for pred in predictions)


class TestFeatureOrder:
    def test_feature_order_combines_categorical_and_numerical(self):
        """Test that FEATURE_ORDER correctly combines categorical and numerical features"""
        expected_order = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)
        assert FEATURE_ORDER == expected_order

    def test_feature_order_no_duplicates(self):
        """Test that FEATURE_ORDER has no duplicate features"""
        assert len(FEATURE_ORDER) == len(set(FEATURE_ORDER))
