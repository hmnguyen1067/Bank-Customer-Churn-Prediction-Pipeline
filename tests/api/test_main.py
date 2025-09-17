from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.loader import ModelBundle
from api.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_bundle_in_app_state():
    """Mock bundle in app state"""
    bundle = MagicMock(spec=ModelBundle)
    bundle.metadata = {
        "model": {"name": "test_model", "version": 1},
        "preprocessor": {"name": "test_preprocessor", "version": 1},
    }
    bundle.feature_order = ["feature1", "feature2", "feature3"]
    app.state.bundle = bundle
    return bundle


class TestHealthEndpoint:
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"Status": "OK"}


class TestReadyEndpoint:
    def test_ready_endpoint_with_model_loaded(self, client, mock_bundle_in_app_state):
        """Test ready endpoint when model is loaded"""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"Status": "READY"}

    def test_ready_endpoint_without_model(self, client):
        """Test ready endpoint when model is not loaded"""
        # Ensure no bundle in app state
        app.state.bundle = None

        response = client.get("/ready")
        assert response.status_code == 503
        assert "Model not loaded" in response.json()["detail"]


class TestMetadataEndpoint:
    def test_metadata_endpoint_with_model_loaded(
        self, client, mock_bundle_in_app_state
    ):
        """Test metadata endpoint when model is loaded"""
        response = client.get("/metadata")
        assert response.status_code == 200

        data = response.json()
        assert "model" in data
        assert "preprocessor" in data
        assert "feature_order" in data
        assert data["feature_order"] == ["feature1", "feature2", "feature3"]

    def test_metadata_endpoint_without_model(self, client):
        """Test metadata endpoint when model is not loaded"""
        app.state.bundle = None

        response = client.get("/metadata")
        assert response.status_code == 503
        assert "Model not loaded" in response.json()["detail"]


class TestPredictEndpoint:
    def test_predict_endpoint_with_valid_data(
        self, client, mock_bundle_in_app_state, sample_prediction_request
    ):
        """Test predict endpoint with valid data"""
        # Mock the prediction functions
        with (
            patch("api.main.validate_and_frame") as mock_validate,
            patch("api.main.predict_labels") as mock_predict,
        ):
            mock_df = MagicMock()
            mock_validate.return_value = mock_df
            mock_predict.return_value = [1]

            response = client.post("/predict", json=sample_prediction_request)

            assert response.status_code == 200

            data = response.json()
            assert "predictions" in data
            assert "model" in data
            assert "preprocessor" in data
            assert "feature_order" in data
            assert data["predictions"] == [1]

            # Check that functions were called correctly
            mock_validate.assert_called_once_with(
                sample_prediction_request["instances"]
            )
            mock_predict.assert_called_once_with(mock_bundle_in_app_state, mock_df)

    def test_predict_endpoint_validation_error(self, client, mock_bundle_in_app_state):
        """Test predict endpoint with validation error"""
        invalid_request = {"instances": [{"invalid": "data"}]}

        with patch("api.main.validate_and_frame") as mock_validate:
            from api.inference import ValidationError

            mock_validate.side_effect = ValidationError("Invalid data")

            response = client.post("/predict", json=invalid_request)

            assert response.status_code == 422
            assert "Invalid data" in response.json()["detail"]

    def test_predict_endpoint_prediction_error(
        self, client, mock_bundle_in_app_state, sample_prediction_request
    ):
        """Test predict endpoint with prediction error"""
        with (
            patch("api.main.validate_and_frame") as mock_validate,
            patch("api.main.predict_labels") as mock_predict,
        ):
            mock_validate.return_value = MagicMock()
            mock_predict.side_effect = Exception("Prediction failed")

            response = client.post("/predict", json=sample_prediction_request)

            assert response.status_code == 500
            assert "Prediction failed" in response.json()["detail"]

    def test_predict_endpoint_without_model(self, client, sample_prediction_request):
        """Test predict endpoint when model is not loaded"""
        app.state.bundle = None

        response = client.post("/predict", json=sample_prediction_request)
        assert response.status_code == 503
        assert "Model not loaded" in response.json()["detail"]


class TestLifespan:
    @patch("api.main.load_bundle")
    @patch("api.main.os.getenv")
    def test_lifespan_successful_model_loading(self, mock_getenv, mock_load_bundle):
        """Test successful model loading during lifespan"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default: default

        # Mock successful bundle loading
        mock_bundle = MagicMock()
        mock_load_bundle.return_value = mock_bundle

        # Test lifespan context manager
        with TestClient(app) as _:
            # Bundle should be loaded into app state
            assert hasattr(app.state, "bundle")
            assert app.state.bundle == mock_bundle

    @patch("api.main.load_bundle")
    @patch("api.main.os.getenv")
    def test_lifespan_model_loading_failure(self, mock_getenv, mock_load_bundle):
        """Test model loading failure during lifespan"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default: default

        # Mock failed bundle loading
        mock_load_bundle.side_effect = Exception("Failed to load model")

        # Test lifespan context manager
        with TestClient(app) as _:
            # Bundle should be None when loading fails
            assert app.state.bundle is None

    @patch("api.main.load_bundle")
    @patch("api.main.os.getenv")
    def test_lifespan_uses_environment_variables(self, mock_getenv, mock_load_bundle):
        """Test that lifespan uses environment variables when available"""
        # Mock environment variables
        custom_values = {
            "MLFLOW_TRACKING_URI": "http://custom:5000",
            "PREPROCESSOR_MODEL_NAME": "CustomPreprocessor",
            "XGB_MODEL_NAME": "CustomModel",
        }
        mock_getenv.side_effect = lambda key, default: custom_values.get(key, default)

        mock_bundle = MagicMock()
        mock_load_bundle.return_value = mock_bundle

        with TestClient(app):
            # Check that load_bundle was called with custom values
            mock_load_bundle.assert_called_once_with(
                tracking_uri="http://custom:5000",
                preprocessor_name="CustomPreprocessor",
                model_name="CustomModel",
            )


class TestAppConfiguration:
    def test_app_title(self):
        """Test that the app has correct title"""
        assert app.title == "Churn Prediction API"

    def test_app_endpoints_exist(self):
        """Test that all expected endpoints exist"""
        routes = [route.path for route in app.routes]

        expected_routes = ["/health", "/ready", "/metadata", "/predict"]

        for route in expected_routes:
            assert route in routes
