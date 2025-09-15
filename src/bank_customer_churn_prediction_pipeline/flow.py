import mlflow
import numpy as np
import pandas as pd
from prefect import flow, task

from .constants import (
    MLFLOW_EXPERIMENT_NAME,
    DEFAULT_SEED,
    MLFLOW_TRACKING_URI,
    PREPROCESSOR_MODEL_NAME,
    XGB_MODEL_NAME,
    MLFLOW_RUNNAME_PREFIX,
    EVIDENTLY_TRACKING_URI,
    EVIDENTLY_PROJECT,
    NUM_TRIALS,
)
from .data_io import read_data, split_data

# from .evidently_report import generate_evidently_report
from .preprocessing import preprocess_data
from .training import (
    optuna_tuning,
    train_best_xgb_model,
    plot_feature_importance,
)
from .monitoring import (
    create_evidently_data_def,
    create_evidently_dataset,
    generate_evidently_report,
    upload_report,
    prepare_monitoring_data,
    create_db,
    insert_metrics_to_db,
)


@task(retries=3, retry_delay_seconds=[2, 5, 15])
def load_data(data_path: str, seed: int) -> pd.DataFrame:
    return split_data(read_data(data_path), seed)


@task
def preprocess(X_train: pd.DataFrame, X_val: pd.DataFrame):
    return preprocess_data(X_train, X_val)


@task
def hyperparameter_tuning(
    X_train: np.ndarray,
    y_train: pd.Series,
    X_val: np.ndarray,
    y_val: pd.Series,
    runname_prefix: str,
    n_trials: int,
):
    best_params = optuna_tuning(
        X_train, y_train, X_val, y_val, runname_prefix=runname_prefix, n_trials=n_trials
    )
    return best_params


@task
def train_model(
    X_train: np.ndarray, y_train: pd.Series, best_params: dict, feat_names=None
):
    with mlflow.start_run():
        xgb_model = train_best_xgb_model(X_train, y_train, best_params)
        mlflow.xgboost.log_model(
            xgb_model,
            name="mlflow_model",
            input_example=X_train[:5],
            registered_model_name=XGB_MODEL_NAME,
        )

        dataset = mlflow.data.from_numpy(X_train, targets=y_train)
        mlflow.log_input(dataset, context="training_best_model")

        importances = plot_feature_importance(xgb_model, feat_names=feat_names)
        mlflow.log_figure(importances, artifact_file="feature_importance.png")


@task
def load_registered_artifacts(
    pp_name: str = PREPROCESSOR_MODEL_NAME, model_name: str = XGB_MODEL_NAME
):
    preprocessor = mlflow.sklearn.load_model(f"models:/{pp_name}/latest")
    model = mlflow.xgboost.load_model(f"models:/{model_name}/latest")
    return preprocessor, model


@task
def create_drift_report(
    X_tr: pd.DataFrame,
    y_tr: pd.Series,
    X_t: pd.DataFrame,
    y_t: pd.Series,
    preprocessor,
    model,
    evidently_uri=EVIDENTLY_TRACKING_URI,
    proj_name=EVIDENTLY_PROJECT,
):
    data_definition = create_evidently_data_def()

    X_tr = prepare_monitoring_data(X_tr, preprocessor, model)
    X_t = prepare_monitoring_data(X_t, preprocessor, model)

    current_data = create_evidently_dataset(X_tr, y_tr, data_definition)
    ref_data = create_evidently_dataset(X_t, y_t, data_definition)

    report = generate_evidently_report(current_data, ref_data)

    upload_report(report, evidently_uri, proj_name)

    metrics = report.dict()["metrics"]
    return metrics


@task
def grafana_monitor(metrics):
    create_db()
    insert_metrics_to_db(metrics)


@flow(name="bank-churn-prefect-flow")
def churn_flow(
    data_path: str,
    mlflow_uri: str = MLFLOW_TRACKING_URI,
    experiment_name: str = MLFLOW_EXPERIMENT_NAME,
    runname_prefix: str = MLFLOW_RUNNAME_PREFIX,
    evidently_uri: str = EVIDENTLY_TRACKING_URI,
    proj_name: str = EVIDENTLY_PROJECT,
    trials: int = NUM_TRIALS,
    seed: int = DEFAULT_SEED,
):
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment_name)

    X_train, y_train, X_val, y_val, X_test, y_test = load_data.submit(
        data_path, seed
    ).result()

    X_train_tf, X_val_tf, feature_names = preprocess.submit(X_train, X_val).result()

    best_params = hyperparameter_tuning.submit(
        X_train_tf, y_train, X_val_tf, y_val, runname_prefix, trials
    ).result()
    X_trv, y_trv = (
        np.append(X_train_tf, X_val_tf, axis=0),
        np.append(y_train, y_val, axis=0),
    )

    train_model.submit(X_trv, y_trv, best_params, feature_names).result()

    preprocessor, model = load_registered_artifacts.submit().result()

    X_data, y_data = (
        pd.concat([X_train, X_val], axis=0),
        np.append(y_train, y_val, axis=0),
    )

    metrics = create_drift_report.submit(
        X_data, y_data, X_test, y_test, preprocessor, model, evidently_uri, proj_name
    ).result()
