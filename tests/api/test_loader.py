from unittest.mock import MagicMock, patch

from api.loader import ModelBundle, _get_latest_version, load_bundle
from api.serving_constants import (CATEGORICAL_FEATURES, MLFLOW_TRACKING_URI,
                                   NUMERICAL_FEATURES, PREPROCESSOR_MODEL_NAME,
                                   XGB_MODEL_NAME)


class TestModelBundle:
    def test_model_bundle_creation(self):
        """Test ModelBundle dataclass creation"""
        preprocessor = MagicMock()
        model = MagicMock()
        feature_order = ["feature1", "feature2"]
        metadata = {"test": "data"}

        bundle = ModelBundle(
            preprocessor=preprocessor,
            model=model,
            feature_order=feature_order,
            metadata=metadata,
        )

        assert bundle.preprocessor == preprocessor
        assert bundle.model == model
        assert bundle.feature_order == feature_order
        assert bundle.metadata == metadata


class TestGetLatestVersion:
    def test_get_latest_version_with_versions(self):
        """Test getting latest version when versions exist"""
        mock_client = MagicMock()
        mock_version1 = MagicMock()
        mock_version1.version = "1"
        mock_version2 = MagicMock()
        mock_version2.version = "3"
        mock_version3 = MagicMock()
        mock_version3.version = "2"

        mock_client.search_model_versions.return_value = [
            mock_version1,
            mock_version2,
            mock_version3,
        ]

        result = _get_latest_version(mock_client, "test_model")

        assert result == 3
        mock_client.search_model_versions.assert_called_once_with("name='test_model'")

    def test_get_latest_version_no_versions(self):
        """Test getting latest version when no versions exist"""
        mock_client = MagicMock()
        mock_client.search_model_versions.return_value = []

        result = _get_latest_version(mock_client, "test_model")

        assert result is None

    def test_get_latest_version_exception(self):
        """Test getting latest version when exception occurs"""
        mock_client = MagicMock()
        mock_client.search_model_versions.side_effect = Exception("Test error")

        result = _get_latest_version(mock_client, "test_model")

        assert result is None


class TestLoadBundle:
    @patch("api.loader.MlflowClient")
    @patch("api.loader.mlflow")
    def test_load_bundle_default_parameters(self, mock_mlflow, mock_mlflow_client):
        """Test load_bundle with default parameters"""
        # Mock MLflow components
        mock_preprocessor = MagicMock()
        mock_model = MagicMock()
        mock_mlflow.sklearn.load_model.return_value = mock_preprocessor
        mock_mlflow.xgboost.load_model.return_value = mock_model

        # Mock client
        mock_client = MagicMock()
        mock_mlflow_client.return_value = mock_client
        mock_client.search_model_versions.return_value = []

        bundle = load_bundle()

        # Check MLflow setup
        mock_mlflow.set_tracking_uri.assert_called_once_with(MLFLOW_TRACKING_URI)

        # Check model loading
        mock_mlflow.sklearn.load_model.assert_called_once_with(
            f"models:/{PREPROCESSOR_MODEL_NAME}/latest"
        )
        mock_mlflow.xgboost.load_model.assert_called_once_with(
            f"models:/{XGB_MODEL_NAME}/latest"
        )

        # Check bundle properties
        assert isinstance(bundle, ModelBundle)
        assert bundle.preprocessor == mock_preprocessor
        assert bundle.model == mock_model

    @patch("api.loader.MlflowClient")
    @patch("api.loader.mlflow")
    def test_load_bundle_custom_parameters(self, mock_mlflow, mock_mlflow_client):
        """Test load_bundle with custom parameters"""
        custom_uri = "http://custom:5000"
        custom_preprocessor = "CustomPreprocessor"
        custom_model = "CustomModel"

        mock_preprocessor = MagicMock()
        mock_model = MagicMock()
        mock_mlflow.sklearn.load_model.return_value = mock_preprocessor
        mock_mlflow.xgboost.load_model.return_value = mock_model

        mock_client = MagicMock()
        mock_mlflow_client.return_value = mock_client
        mock_client.search_model_versions.return_value = []

        _ = load_bundle(
            tracking_uri=custom_uri,
            preprocessor_name=custom_preprocessor,
            model_name=custom_model,
        )

        # Check custom parameters were used
        mock_mlflow.set_tracking_uri.assert_called_once_with(custom_uri)
        mock_mlflow.sklearn.load_model.assert_called_once_with(
            f"models:/{custom_preprocessor}/latest"
        )
        mock_mlflow.xgboost.load_model.assert_called_once_with(
            f"models:/{custom_model}/latest"
        )

    @patch("api.loader.MlflowClient")
    @patch("api.loader.mlflow")
    def test_load_bundle_feature_order(self, mock_mlflow, mock_mlflow_client):
        """Test that load_bundle sets correct feature order"""
        mock_mlflow.sklearn.load_model.return_value = MagicMock()
        mock_mlflow.xgboost.load_model.return_value = MagicMock()

        mock_client = MagicMock()
        mock_mlflow_client.return_value = mock_client
        mock_client.search_model_versions.return_value = []

        bundle = load_bundle()

        expected_feature_order = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)
        assert bundle.feature_order == expected_feature_order

    @patch("api.loader.MlflowClient")
    @patch("api.loader.mlflow")
    def test_load_bundle_metadata(self, mock_mlflow, mock_mlflow_client):
        """Test that load_bundle creates correct metadata"""
        mock_mlflow.sklearn.load_model.return_value = MagicMock()
        mock_mlflow.xgboost.load_model.return_value = MagicMock()

        mock_client = MagicMock()
        mock_mlflow_client.return_value = mock_client

        # Mock version search to return specific versions
        def side_effect(query):
            if "ChurnDataPreprocessor" in query:
                mock_version = MagicMock()
                mock_version.version = "2"
                return [mock_version]
            elif "XGBoostChurnModel" in query:
                mock_version = MagicMock()
                mock_version.version = "3"
                return [mock_version]
            return []

        mock_client.search_model_versions.side_effect = side_effect

        bundle = load_bundle()

        # Check metadata structure
        assert "preprocessor" in bundle.metadata
        assert "model" in bundle.metadata
        assert "feature_order" in bundle.metadata

        # Check preprocessor metadata
        assert bundle.metadata["preprocessor"]["name"] == PREPROCESSOR_MODEL_NAME
        assert bundle.metadata["preprocessor"]["version"] == 2

        # Check model metadata
        assert bundle.metadata["model"]["name"] == XGB_MODEL_NAME
        assert bundle.metadata["model"]["version"] == 3

        # Check feature order in metadata
        expected_feature_order = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)
        assert bundle.metadata["feature_order"] == expected_feature_order

    @patch("api.loader.MlflowClient")
    @patch("api.loader.mlflow")
    def test_load_bundle_version_handling(self, mock_mlflow, mock_mlflow_client):
        """Test version handling when no versions are found"""
        mock_mlflow.sklearn.load_model.return_value = MagicMock()
        mock_mlflow.xgboost.load_model.return_value = MagicMock()

        mock_client = MagicMock()
        mock_mlflow_client.return_value = mock_client
        mock_client.search_model_versions.return_value = []  # No versions found

        bundle = load_bundle()

        # Should handle None versions gracefully
        assert bundle.metadata["preprocessor"]["version"] is None
        assert bundle.metadata["model"]["version"] is None

    @patch("api.loader.MlflowClient")
    @patch("api.loader.mlflow")
    def test_load_bundle_mlflow_integration(self, mock_mlflow, mock_mlflow_client):
        """Test MLflow integration in load_bundle"""
        mock_mlflow.sklearn.load_model.return_value = MagicMock()
        mock_mlflow.xgboost.load_model.return_value = MagicMock()

        mock_client = MagicMock()
        mock_mlflow_client.return_value = mock_client
        mock_client.search_model_versions.return_value = []

        load_bundle()

        # Check that MLflow client was created
        mock_mlflow_client.assert_called_once()

        # Check that version searches were performed
        expected_calls = [
            f"name='{PREPROCESSOR_MODEL_NAME}'",
            f"name='{XGB_MODEL_NAME}'",
        ]

        actual_calls = [
            call[0][0] for call in mock_client.search_model_versions.call_args_list
        ]
        assert len(actual_calls) == 2
        assert all(call in actual_calls for call in expected_calls)
