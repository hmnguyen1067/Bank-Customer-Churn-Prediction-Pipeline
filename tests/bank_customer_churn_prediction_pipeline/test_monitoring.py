from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from evidently import DataDefinition, Dataset

from bank_customer_churn_prediction_pipeline.constants import (
    CATEGORICAL_FEATURES, EVIDENTLY_PROJECT, EVIDENTLY_TRACKING_URI,
    NUMERICAL_FEATURES, PREDICTION_COL, TARGET)
from bank_customer_churn_prediction_pipeline.monitoring import (
    create_evidently_data_def, create_evidently_dataset,
    generate_evidently_report, insert_metrics_to_db, prepare_monitoring_data,
    upload_report)


class TestCreateEvidentlyDataDef:
    def test_create_evidently_data_def_returns_definition(self):
        """Test that create_evidently_data_def returns a DataDefinition"""
        data_def = create_evidently_data_def()
        assert isinstance(data_def, DataDefinition)

    def test_create_evidently_data_def_correct_columns(self):
        """Test that data definition has correct column assignments"""
        data_def = create_evidently_data_def()

        # Check numerical columns
        assert data_def.numerical_columns == NUMERICAL_FEATURES

        # Check categorical columns include the expected features plus target and prediction
        expected_categorical = CATEGORICAL_FEATURES + [PREDICTION_COL] + [TARGET]
        assert data_def.categorical_columns == expected_categorical


class TestCreateEvidentlyDataset:
    def test_create_evidently_dataset_returns_dataset(
        self, sample_features, sample_targets
    ):
        """Test that create_evidently_dataset returns a Dataset"""
        data_def = create_evidently_data_def()
        dataset = create_evidently_dataset(sample_features, sample_targets, data_def)

        assert isinstance(dataset, Dataset)


class TestPrepareMonitoringData:
    @patch("bank_customer_churn_prediction_pipeline.monitoring.make_predictions")
    def test_prepare_monitoring_data_adds_predictions(
        self, mock_make_predictions, sample_features
    ):
        """Test that prepare_monitoring_data adds prediction column"""
        mock_preprocessor = MagicMock()
        mock_model = MagicMock()
        mock_predictions = np.array([0, 1, 0])
        mock_make_predictions.return_value = mock_predictions

        result = prepare_monitoring_data(sample_features, mock_preprocessor, mock_model)

        # Should call make_predictions with correct arguments
        mock_make_predictions.assert_called_once_with(
            mock_model, sample_features, mock_preprocessor
        )

        # Should add prediction column
        assert PREDICTION_COL in result.columns
        assert all(result[PREDICTION_COL].values == mock_predictions)

    @patch("bank_customer_churn_prediction_pipeline.monitoring.make_predictions")
    def test_prepare_monitoring_data_preserves_original_data(
        self, mock_make_predictions, sample_features
    ):
        """Test that original features are preserved"""
        mock_preprocessor = MagicMock()
        mock_model = MagicMock()
        mock_predictions = np.array([0, 1, 0])
        mock_make_predictions.return_value = mock_predictions

        result = prepare_monitoring_data(sample_features, mock_preprocessor, mock_model)

        # Original columns should be preserved
        for col in sample_features.columns:
            assert col in result.columns
            pd.testing.assert_series_equal(result[col], sample_features[col])


class TestGenerateEvidentlyReport:
    @patch("bank_customer_churn_prediction_pipeline.monitoring.Report")
    def test_generate_evidently_report_creates_report(
        self, mock_report_class, sample_features, sample_targets
    ):
        """Test that generate_evidently_report creates a Report"""
        data_def = create_evidently_data_def()
        current_data = create_evidently_dataset(
            sample_features, sample_targets, data_def
        )
        reference_data = create_evidently_dataset(
            sample_features, sample_targets, data_def
        )

        mock_report_instance = MagicMock()
        mock_report_class.return_value = mock_report_instance
        mock_report_instance.run.return_value = mock_report_instance

        result = generate_evidently_report(current_data, reference_data)

        # Check that Report was created with correct metrics
        mock_report_class.assert_called_once()
        call_args = mock_report_class.call_args[0][
            0
        ]  # First positional argument (metrics list)
        assert len(call_args) == 4  # Should have 4 metrics

        # Check that run was called
        mock_report_instance.run.assert_called_once_with(
            current_data, reference_data=reference_data
        )

        assert result == mock_report_instance


class TestUploadReport:
    @patch("bank_customer_churn_prediction_pipeline.monitoring.RemoteWorkspace")
    def test_upload_report_creates_workspace(self, mock_workspace_class):
        """Test that upload_report creates a RemoteWorkspace"""
        mock_report = MagicMock()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock existing project
        mock_project = MagicMock()
        mock_project.id = "test_project_id"
        mock_workspace.search_project.return_value = [mock_project]
        mock_workspace.get_project.return_value = mock_project

        upload_report(mock_report)

        # Check workspace creation
        mock_workspace_class.assert_called_once_with(EVIDENTLY_TRACKING_URI)

        # Check project search
        mock_workspace.search_project.assert_called_once_with(EVIDENTLY_PROJECT)

        # Check add_run call
        mock_workspace.add_run.assert_called_once_with(mock_project.id, mock_report)

    @patch("bank_customer_churn_prediction_pipeline.monitoring.RemoteWorkspace")
    def test_upload_report_creates_new_project(self, mock_workspace_class):
        """Test upload_report creates new project when none exists"""
        mock_report = MagicMock()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock no existing project
        mock_workspace.search_project.return_value = []
        mock_new_project = MagicMock()
        mock_new_project.id = "new_project_id"
        mock_workspace.create_project.return_value = mock_new_project

        upload_report(mock_report)

        # Check project creation
        mock_workspace.create_project.assert_called_once_with(EVIDENTLY_PROJECT)
        mock_workspace.add_run.assert_called_once_with(mock_new_project.id, mock_report)

    @patch("bank_customer_churn_prediction_pipeline.monitoring.RemoteWorkspace")
    def test_upload_report_custom_parameters(self, mock_workspace_class):
        """Test upload_report with custom parameters"""
        mock_report = MagicMock()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        custom_uri = "http://custom:8000"
        custom_project = "Custom Project"

        # Mock existing project
        mock_project = MagicMock()
        mock_project.id = "custom_project_id"
        mock_workspace.search_project.return_value = [mock_project]
        mock_workspace.get_project.return_value = mock_project

        upload_report(mock_report, evidently_uri=custom_uri, proj_name=custom_project)

        # Check custom parameters were used
        mock_workspace_class.assert_called_once_with(custom_uri)
        mock_workspace.search_project.assert_called_once_with(custom_project)


class TestInsertMetricsToDB:
    @patch("bank_customer_churn_prediction_pipeline.monitoring.psycopg")
    @patch("bank_customer_churn_prediction_pipeline.monitoring.datetime")
    def test_insert_metrics_to_db_inserts_correctly(self, mock_datetime, mock_psycopg):
        """Test that insert_metrics_to_db inserts metrics correctly"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock datetime
        mock_now = MagicMock()
        mock_datetime.datetime.now.return_value = mock_now

        # Sample metrics
        metrics = [
            {"value": 0.15},  # prediction_drift
            {"value": {"count": 3}},  # num_drifted_columns
            {"value": {"share": 0.02}},  # share_missing_values
        ]

        insert_metrics_to_db(metrics)

        # Check cursor execute was called with correct parameters
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args

        # Check SQL query
        sql_query = call_args[0][0]
        assert "insert into metrics" in sql_query
        assert "timestamp" in sql_query
        assert "prediction_drift" in sql_query
        assert "num_drifted_columns" in sql_query
        assert "share_missing_values" in sql_query

        # Check parameters
        params = call_args[0][1]
        assert params == (mock_now, 0.15, 3, 0.02)

    @patch("bank_customer_churn_prediction_pipeline.monitoring.psycopg")
    def test_insert_metrics_to_db_extracts_values_correctly(self, mock_psycopg):
        """Test that metrics values are extracted correctly"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Sample metrics with different structure
        metrics = [{"value": 0.25}, {"value": {"count": 5}}, {"value": {"share": 0.05}}]

        insert_metrics_to_db(metrics)

        # Check that the correct values were extracted
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # Should extract: 0.25, 5, 0.05 (plus timestamp)
        assert params[1] == 0.25  # prediction_drift
        assert params[2] == 5  # num_drifted_columns
        assert params[3] == 0.05  # share_missing_values
