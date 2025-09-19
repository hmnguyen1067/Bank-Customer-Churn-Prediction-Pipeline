from unittest.mock import MagicMock, patch

import numpy as np

from bank_customer_churn_prediction_pipeline.constants import (
    EVIDENTLY_PROJECT, EVIDENTLY_TRACKING_URI, PREPROCESSOR_MODEL_NAME,
    XGB_MODEL_NAME)
from bank_customer_churn_prediction_pipeline.flow import (
    create_drift_report, grafana_monitor, hyperparameter_tuning, load_data,
    load_registered_artifacts, preprocess, train_model)


class TestLoadDataTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.split_data")
    @patch("bank_customer_churn_prediction_pipeline.flow.read_data")
    def test_load_data_task(self, mock_read_data, mock_split_data, sample_data):
        """Test load_data task"""
        data_path = "test_path.csv"
        seed = 42

        mock_read_data.return_value = sample_data
        mock_split_data.return_value = (
            sample_data.iloc[:2],
            [0, 1],  # X_train, y_train
            sample_data.iloc[2:3],
            [1],  # X_val, y_val
            sample_data.iloc[3:4],
            [0],  # X_test, y_test
        )

        result = load_data(data_path, seed)

        mock_read_data.assert_called_once_with(data_path)
        mock_split_data.assert_called_once_with(sample_data, seed)
        assert len(result) == 6  # Returns 6 components

    @patch("bank_customer_churn_prediction_pipeline.flow.split_data")
    @patch("bank_customer_churn_prediction_pipeline.flow.read_data")
    def test_load_data_task_with_retry(
        self, mock_read_data, mock_split_data, sample_data
    ):
        """Test that load_data task has retry configuration"""
        # Check that the task has retry configuration
        assert load_data.retries == 3
        assert load_data.retry_delay_seconds == [2, 5, 15]


class TestPreprocessTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.preprocess_data")
    def test_preprocess_task(self, mock_preprocess_data, sample_features):
        """Test preprocess task"""
        X_train = sample_features.copy()
        X_val = sample_features.copy()

        mock_transformed_train = np.random.rand(3, 10)
        mock_transformed_val = np.random.rand(3, 10)
        mock_feature_names = ["feature_1", "feature_2"]

        mock_preprocess_data.return_value = (
            mock_transformed_train,
            mock_transformed_val,
            mock_feature_names,
        )

        result = preprocess(X_train, X_val)

        mock_preprocess_data.assert_called_once_with(X_train, X_val)
        assert len(result) == 3  # Returns transformed data and feature names


class TestHyperparameterTuningTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.optuna_tuning")
    def test_hyperparameter_tuning_task(self, mock_optuna_tuning):
        """Test hyperparameter tuning task"""
        X_train = np.random.rand(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.rand(50, 10)
        y_val = np.random.randint(0, 2, 50)
        runname_prefix = "test_prefix"
        n_trials = 10

        mock_best_params = {"n_estimators": 100, "learning_rate": 0.1}
        mock_optuna_tuning.return_value = mock_best_params

        result = hyperparameter_tuning(
            X_train, y_train, X_val, y_val, runname_prefix, n_trials
        )

        mock_optuna_tuning.assert_called_once_with(
            X_train,
            y_train,
            X_val,
            y_val,
            runname_prefix=runname_prefix,
            n_trials=n_trials,
        )
        assert result == mock_best_params


class TestTrainModelTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.mlflow")
    @patch("bank_customer_churn_prediction_pipeline.flow.train_best_xgb_model")
    def test_train_model_task(
        self, mock_train_model, mock_mlflow
    ):
        """Test train_model task"""
        X_train = np.random.rand(100, 10)
        y_train = np.random.randint(0, 2, 100)
        best_params = {"n_estimators": 100, "learning_rate": 0.1}

        mock_model = MagicMock()
        mock_train_model.return_value = mock_model

        mock_dataset = MagicMock()
        mock_mlflow.data.from_numpy.return_value = mock_dataset

        train_model(X_train, y_train, best_params)

        # Check model training
        mock_train_model.assert_called_once_with(X_train, y_train, best_params)

        # Check MLflow logging
        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.xgboost.log_model.assert_called_once()
        mock_mlflow.data.from_numpy.assert_called_once_with(X_train, targets=y_train)
        mock_mlflow.log_input.assert_called_once()


class TestLoadRegisteredArtifactsTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.mlflow")
    def test_load_registered_artifacts_default(self, mock_mlflow):
        """Test load_registered_artifacts with default parameters"""
        mock_preprocessor = MagicMock()
        mock_model = MagicMock()

        mock_mlflow.sklearn.load_model.return_value = mock_preprocessor
        mock_mlflow.xgboost.load_model.return_value = mock_model

        preprocessor, model = load_registered_artifacts()

        # Check default model names are used
        mock_mlflow.sklearn.load_model.assert_called_once_with(
            f"models:/{PREPROCESSOR_MODEL_NAME}/latest"
        )
        mock_mlflow.xgboost.load_model.assert_called_once_with(
            f"models:/{XGB_MODEL_NAME}/latest"
        )

        assert preprocessor == mock_preprocessor
        assert model == mock_model

    @patch("bank_customer_churn_prediction_pipeline.flow.mlflow")
    def test_load_registered_artifacts_custom_names(self, mock_mlflow):
        """Test load_registered_artifacts with custom model names"""
        custom_pp_name = "CustomPreprocessor"
        custom_model_name = "CustomModel"

        mock_preprocessor = MagicMock()
        mock_model = MagicMock()

        mock_mlflow.sklearn.load_model.return_value = mock_preprocessor
        mock_mlflow.xgboost.load_model.return_value = mock_model

        load_registered_artifacts(custom_pp_name, custom_model_name)

        mock_mlflow.sklearn.load_model.assert_called_once_with(
            f"models:/{custom_pp_name}/latest"
        )
        mock_mlflow.xgboost.load_model.assert_called_once_with(
            f"models:/{custom_model_name}/latest"
        )


class TestCreateDriftReportTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.upload_report")
    @patch("bank_customer_churn_prediction_pipeline.flow.generate_evidently_report")
    @patch("bank_customer_churn_prediction_pipeline.flow.create_evidently_dataset")
    @patch("bank_customer_churn_prediction_pipeline.flow.prepare_monitoring_data")
    @patch("bank_customer_churn_prediction_pipeline.flow.create_evidently_data_def")
    def test_create_drift_report_task(
        self,
        mock_data_def,
        mock_prepare_data,
        mock_create_dataset,
        mock_generate_report,
        mock_upload_report,
        sample_features,
        sample_targets,
    ):
        """Test create_drift_report task"""
        X_tr = sample_features.copy()
        y_tr = sample_targets.copy()
        X_t = sample_features.copy()
        y_t = sample_targets.copy()
        preprocessor = MagicMock()
        model = MagicMock()

        # Mock returns
        mock_data_definition = MagicMock()
        mock_data_def.return_value = mock_data_definition

        mock_prepared_tr = sample_features.copy()
        mock_prepared_t = sample_features.copy()
        mock_prepare_data.side_effect = [mock_prepared_tr, mock_prepared_t]

        mock_current_dataset = MagicMock()
        mock_ref_dataset = MagicMock()
        mock_create_dataset.side_effect = [mock_current_dataset, mock_ref_dataset]

        mock_report = MagicMock()
        mock_report.dict.return_value = {"metrics": [{"test": "data"}]}
        mock_generate_report.return_value = mock_report

        result = create_drift_report(X_tr, y_tr, X_t, y_t, preprocessor, model)

        # Check function calls
        mock_data_def.assert_called_once()
        assert mock_prepare_data.call_count == 2
        assert mock_create_dataset.call_count == 2
        mock_generate_report.assert_called_once_with(
            mock_current_dataset, mock_ref_dataset
        )
        mock_upload_report.assert_called_once_with(
            mock_report, EVIDENTLY_TRACKING_URI, EVIDENTLY_PROJECT
        )

        assert result == [{"test": "data"}]


class TestGrafanaMonitorTask:
    @patch("bank_customer_churn_prediction_pipeline.flow.insert_metrics_to_db")
    @patch("bank_customer_churn_prediction_pipeline.flow.create_db")
    def test_grafana_monitor_task(self, mock_create_db, mock_insert_metrics):
        """Test grafana_monitor task"""
        metrics = [{"test": "metrics"}]

        grafana_monitor(metrics)

        mock_create_db.assert_called_once()
        mock_insert_metrics.assert_called_once_with(metrics)
