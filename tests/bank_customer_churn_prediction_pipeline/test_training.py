from unittest.mock import MagicMock, call, patch

import numpy as np
import optuna
import xgboost as xgb

from bank_customer_churn_prediction_pipeline.constants import (
    DEFAULT_SEED, MLFLOW_RUNNAME_PREFIX)
from bank_customer_churn_prediction_pipeline.training import (
    XGBObjective, make_predictions, optuna_tuning,
    train_best_xgb_model)


class TestXGBObjective:
    def test_xgb_objective_initialization(self, sample_features, sample_targets):
        """Test XGBObjective initialization"""
        X_train = sample_features.values
        y_train = sample_targets.values
        X_val = sample_features.values
        y_val = sample_targets.values

        objective = XGBObjective(X_train, y_train, X_val, y_val)

        assert np.array_equal(objective.X_train, X_train)
        assert np.array_equal(objective.y_train, y_train)
        assert np.array_equal(objective.X_val, X_val)
        assert np.array_equal(objective.y_val, y_val)
        assert objective.seed == DEFAULT_SEED

    def test_xgb_objective_custom_seed(self, sample_features, sample_targets):
        """Test XGBObjective with custom seed"""
        X_train = sample_features.values
        y_train = sample_targets.values
        X_val = sample_features.values
        y_val = sample_targets.values
        custom_seed = 123

        objective = XGBObjective(X_train, y_train, X_val, y_val, seed=custom_seed)

        assert objective.seed == custom_seed

    @patch("bank_customer_churn_prediction_pipeline.training.mlflow")
    @patch("bank_customer_churn_prediction_pipeline.training.xgb")
    def test_xgb_objective_call(
        self, mock_xgb, mock_mlflow, sample_features, sample_targets
    ):
        """Test XGBObjective.__call__ method"""
        X_train = sample_features.values
        y_train = sample_targets.values
        X_val = sample_features.values
        y_val = sample_targets.values

        # Mock trial
        mock_trial = MagicMock(spec=optuna.Trial)
        mock_trial.suggest_int.side_effect = [
            100,
            6,
            0,
            1,
        ]  # n_estimators, max_depth, max_delta_step, min_child_weight
        mock_trial.suggest_float.side_effect = [
            0.1,
            1.0,
            1.0,
            0.5,
            0.1,
            1.0,
        ]  # learning_rate, reg_lambda, reg_alpha, subsample, gamma, scale_pos_weight

        # Mock XGBoost components
        mock_train_matrix = MagicMock()
        mock_val_matrix = MagicMock()
        mock_xgb.DMatrix.side_effect = [mock_train_matrix, mock_val_matrix]

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.2, 0.8, 0.1])
        mock_xgb.train.return_value = mock_model

        # Mock MLflow
        mock_mlflow.start_run.return_value.__enter__.return_value = MagicMock()

        objective = XGBObjective(X_train, y_train, X_val, y_val)
        result = objective(mock_trial)

        # Check that XGBoost training was called
        mock_xgb.train.assert_called_once()

        # Check that metrics were logged
        assert mock_mlflow.log_metric.call_count == 2
        assert mock_mlflow.log_params.call_count == 1

        # Result should be a float (ROC AUC score)
        assert isinstance(result, float)

    @patch("bank_customer_churn_prediction_pipeline.training.mlflow")
    @patch("bank_customer_churn_prediction_pipeline.training.f1_score")
    @patch("bank_customer_churn_prediction_pipeline.training.roc_auc_score")
    def test_xgb_objective_metrics_calculation(
        self, mock_roc_auc, mock_f1, mock_mlflow, sample_features, sample_targets
    ):
        """Test that XGBObjective calculates metrics correctly"""
        mock_trial = MagicMock(spec=optuna.Trial)
        mock_trial.suggest_int.side_effect = [100, 6, 0, 1]
        mock_trial.suggest_float.side_effect = [0.1, 1.0, 1.0, 0.5, 0.1, 1.0]

        mock_f1.return_value = 0.75
        mock_roc_auc.return_value = 0.85

        X_train = sample_features.values
        y_train = sample_targets.values
        X_val = sample_features.values
        y_val = sample_targets.values

        with patch("bank_customer_churn_prediction_pipeline.training.xgb"):
            objective = XGBObjective(X_train, y_train, X_val, y_val)
            result = objective(mock_trial)

            # Should return F1
            assert result == 0.75

            # Check metric logging
            mock_mlflow.log_metric.assert_has_calls(
                [call("roc_auc", 0.85), call("f1_score", 0.75)], any_order=True
            )


class TestTrainBestXGBModel:
    @patch("bank_customer_churn_prediction_pipeline.training.xgb")
    def test_train_best_xgb_model(self, mock_xgb, sample_features, sample_targets):
        """Test train_best_xgb_model function"""
        X_train = sample_features.values
        y_train = sample_targets.values
        best_params = {"n_estimators": 100, "learning_rate": 0.1}

        mock_train_matrix = MagicMock()
        mock_xgb.DMatrix.return_value = mock_train_matrix

        mock_model = MagicMock()
        mock_xgb.train.return_value = mock_model

        result = train_best_xgb_model(X_train, y_train, best_params)

        # Check DMatrix creation
        mock_xgb.DMatrix.assert_called_once_with(X_train, label=y_train)

        # Check training call
        mock_xgb.train.assert_called_once_with(best_params, mock_train_matrix)

        assert result == mock_model
    


class TestOptunatuning:
    @patch("bank_customer_churn_prediction_pipeline.training.mlflow")
    @patch("bank_customer_churn_prediction_pipeline.training.optuna")
    @patch("bank_customer_churn_prediction_pipeline.training.datetime")
    def test_optuna_tuning_default_parameters(
        self, mock_datetime, mock_optuna, mock_mlflow, sample_features, sample_targets
    ):
        """Test optuna_tuning with default parameters"""
        X_train = sample_features.values
        y_train = sample_targets.values
        X_val = sample_features.values
        y_val = sample_targets.values

        # Mock datetime
        mock_date = MagicMock()
        mock_datetime.datetime.now.return_value.date.return_value = mock_date

        # Mock study
        mock_study = MagicMock()
        mock_study.best_params = {"n_estimators": 100, "learning_rate": 0.1}
        mock_optuna.create_study.return_value = mock_study

        # Mock MLflow
        mock_mlflow.start_run.return_value.__enter__.return_value = MagicMock()

        result = optuna_tuning(X_train, y_train, X_val, y_val)

        # Check study creation
        mock_optuna.create_study.assert_called_once()
        create_args = mock_optuna.create_study.call_args[1]
        assert create_args["direction"] == "maximize"

        # Check MLflow logging
        mock_mlflow.set_tag.assert_has_calls(
            [call("model", "xgboost"), call("identifier", MLFLOW_RUNNAME_PREFIX)],
            any_order=True,
        )
        mock_mlflow.log_params.assert_called_once_with(mock_study.best_params)

        assert result == mock_study.best_params

    @patch("bank_customer_churn_prediction_pipeline.training.mlflow")
    @patch("bank_customer_churn_prediction_pipeline.training.optuna")
    @patch("bank_customer_churn_prediction_pipeline.training.datetime")
    def test_optuna_tuning_custom_parameters(
        self, mock_datetime, mock_optuna, mock_mlflow, sample_features, sample_targets
    ):
        """Test optuna_tuning with custom parameters"""
        X_train = sample_features.values
        y_train = sample_targets.values
        X_val = sample_features.values
        y_val = sample_targets.values

        custom_runname = "custom_prefix"
        custom_trials = 50

        mock_study = MagicMock()
        mock_study.best_params = {"test": "params"}
        mock_optuna.create_study.return_value = mock_study

        mock_mlflow.start_run.return_value.__enter__.return_value = MagicMock()

        optuna_tuning(
            X_train,
            y_train,
            X_val,
            y_val,
            runname_prefix=custom_runname,
            n_trials=custom_trials,
        )

        mock_mlflow.set_tag.assert_has_calls(
            [call("identifier", custom_runname)], any_order=True
        )


class TestMakePredictions:
    @patch("bank_customer_churn_prediction_pipeline.training.xgb")
    def test_make_predictions_returns_integers(
        self, mock_xgb, mock_preprocessor, sample_features
    ):
        """Test that make_predictions returns integer predictions"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.1, 0.8, 0.3])

        mock_transformed_data = np.random.rand(3, 10)
        mock_preprocessor.transform.return_value = mock_transformed_data

        mock_dmatrix = MagicMock()
        mock_xgb.DMatrix.return_value = mock_dmatrix

        predictions = make_predictions(mock_model, sample_features, mock_preprocessor)

        # Check preprocessing
        mock_preprocessor.transform.assert_called_once_with(sample_features)

        # Check DMatrix creation
        mock_xgb.DMatrix.assert_called_once_with(mock_transformed_data)

        # Check model prediction
        mock_model.predict.assert_called_once_with(mock_dmatrix)

        # Check result
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype == int
        assert all(pred in [0, 1] for pred in predictions)

    @patch("bank_customer_churn_prediction_pipeline.training.xgb")
    def test_make_predictions_rounding(
        self, mock_xgb, mock_preprocessor, sample_features
    ):
        """Test prediction rounding behavior"""
        mock_model = MagicMock()
        # Values that test rounding behavior
        mock_model.predict.return_value = np.array([0.4, 0.5, 0.6])

        mock_preprocessor.transform.return_value = np.random.rand(3, 10)

        predictions = make_predictions(mock_model, sample_features, mock_preprocessor)

        # 0.4 -> 0, 0.5 -> 0 (rounding to nearest even), 0.6 -> 1
        expected = np.array([0, 0, 1])
        np.testing.assert_array_equal(predictions, expected)


class TestMakePredictionsIntegration:
    def test_make_predictions_full_pipeline(self, mock_preprocessor, sample_features):
        """Integration test for make_predictions"""
        # Create a real XGBoost model for testing

        # Create simple training data
        X_simple = np.random.rand(10, 5)
        y_simple = np.random.randint(0, 2, 10)

        # Train a simple model
        dtrain = xgb.DMatrix(X_simple, label=y_simple)
        params = {"objective": "binary:logistic", "eval_metric": "logloss"}
        model = xgb.train(params, dtrain, num_boost_round=1)

        # Mock preprocessor to return compatible data
        mock_preprocessor.transform.return_value = np.random.rand(
            len(sample_features), 5
        )

        predictions = make_predictions(model, sample_features, mock_preprocessor)

        # Should return valid predictions
        assert len(predictions) == len(sample_features)
        assert all(pred in [0, 1] for pred in predictions)
        assert predictions.dtype == int
