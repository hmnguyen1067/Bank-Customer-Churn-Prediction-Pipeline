import os
import tempfile
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer


@pytest.fixture
def sample_data():
    """Sample customer churn data for testing"""
    np.random.seed(42)  # For reproducible test data
    n_samples = 100

    return pd.DataFrame(
        {
            "RowNumber": range(1, n_samples + 1),
            "CustomerId": np.random.randint(10000000, 20000000, n_samples),
            "Surname": [f"Customer_{i}" for i in range(n_samples)],
            "Geography": np.random.choice(["Spain", "France", "Germany"], n_samples),
            "Gender": np.random.choice(["Female", "Male"], n_samples),
            "Age": np.random.randint(18, 80, n_samples),
            "Tenure": np.random.randint(0, 11, n_samples),
            "Balance": np.random.uniform(0, 250000, n_samples),
            "NumOfProducts": np.random.randint(1, 5, n_samples),
            "HasCrCard": np.random.randint(0, 2, n_samples),
            "IsActiveMember": np.random.randint(0, 2, n_samples),
            "EstimatedSalary": np.random.uniform(20000, 200000, n_samples),
            "Exited": np.random.randint(0, 2, n_samples),
            "Satisfaction Score": np.random.randint(1, 6, n_samples),
            "Card Type": np.random.choice(["DIAMOND", "SILVER", "GOLD"], n_samples),
            "Point Earned": np.random.randint(100, 1000, n_samples),
            "CreditScore": np.random.randint(300, 900, n_samples),
            "Complain": np.random.randint(0, 2, n_samples),
        }
    )


@pytest.fixture
def sample_features():
    """Sample feature data without target variable"""
    return pd.DataFrame(
        {
            "Geography": ["Spain", "France", "Germany"],
            "Gender": ["Female", "Male", "Male"],
            "Age": [42, 41, 44],
            "Tenure": [2, 1, 8],
            "Balance": [0.0, 83807.86, 159660.8],
            "NumOfProducts": [1, 1, 3],
            "HasCrCard": [1, 0, 1],
            "IsActiveMember": [1, 1, 0],
            "EstimatedSalary": [101348.88, 112542.58, 113931.57],
            "Satisfaction Score": [2, 3, 3],
            "Card Type": ["DIAMOND", "SILVER", "DIAMOND"],
            "Point Earned": [464, 456, 377],
            "CreditScore": [619, 608, 502],
        }
    )


@pytest.fixture
def sample_targets():
    """Sample target data"""
    return pd.Series([1, 0, 1])


@pytest.fixture
def temp_csv_file(sample_data):
    """Create a temporary CSV file with sample data"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_data.to_csv(f.name, index=False)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_preprocessor():
    """Mock sklearn ColumnTransformer preprocessor"""
    preprocessor = MagicMock(spec=ColumnTransformer)

    # Mock transform methods
    preprocessor.fit_transform.return_value = np.random.rand(100, 20)
    preprocessor.transform.return_value = np.random.rand(50, 20)
    preprocessor.get_feature_names_out.return_value = [
        f"feature_{i}" for i in range(20)
    ]

    return preprocessor


@pytest.fixture
def mock_xgb_model():
    """Mock XGBoost model"""
    model = MagicMock()
    model.predict.return_value = np.array([0.1, 0.8, 0.3, 0.9, 0.2])
    return model


@pytest.fixture
def sample_prediction_request():
    """Sample prediction request data"""
    return {
        "instances": [
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
            }
        ]
    }


@pytest.fixture
def mock_mlflow_model():
    """Mock MLflow model loading"""
    model = MagicMock()
    model.predict.return_value = np.array([0, 1])
    return model


@pytest.fixture
def mock_model_bundle(mock_preprocessor, mock_xgb_model):
    """Mock ModelBundle for API testing"""
    from api.loader import ModelBundle

    bundle = ModelBundle(
        preprocessor=mock_preprocessor,
        model=mock_xgb_model,
        feature_order=[
            "Geography",
            "Gender",
            "Age",
            "Tenure",
            "Balance",
            "NumOfProducts",
            "HasCrCard",
            "IsActiveMember",
            "EstimatedSalary",
            "Satisfaction Score",
            "Card Type",
            "Point Earned",
            "CreditScore",
        ],
        metadata={
            "model": {"name": "test_model", "version": 1},
            "preprocessor": {"name": "test_preprocessor", "version": 1},
        },
    )
    return bundle
