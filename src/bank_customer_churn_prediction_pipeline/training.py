import datetime

import matplotlib
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import optuna
import xgboost as xgb
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.metrics import f1_score, roc_auc_score

from constants import DEFAULT_SEED, MLFLOW_RUNNAME_PREFIX, NUM_TRIALS

sampler = optuna.samplers.TPESampler(seed=DEFAULT_SEED)


class XGBObjective(object):
    def __init__(self, X_train, y_train, X_val, y_val, seed=DEFAULT_SEED):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.seed = seed

    def __call__(self, trial: optuna.Trial) -> float:
        with mlflow.start_run(nested=True):
            train = xgb.DMatrix(self.X_train, label=self.y_train)
            valid = xgb.DMatrix(self.X_val, label=self.y_val)

            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 5000),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 1.0, log=True
                ),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-9, 100.0, log=True),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-9, 100.0, log=True),
                "subsample": trial.suggest_float("subsample", 0.1, 1.0),
                "max_depth": trial.suggest_int("max_depth", 1, 12),
                "max_delta_step": trial.suggest_int("max_delta_step", 0, 10),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "gamma": trial.suggest_float("gamma", 1e-9, 0.5, log=True),
                "scale_pos_weight": trial.suggest_float(
                    "scale_pos_weight", 1e-6, 500.0, log=True
                ),
                "seed": self.seed,
            }

            model = xgb.train(
                params,
                train,
                evals=[(valid, "validation")],
                early_stopping_rounds=300,
                verbose_eval=False,
            )

            preds = model.predict(valid)
            pred_labels = np.clip(np.rint(preds), 0, 1).astype(int)

            f1 = f1_score(self.y_val, pred_labels)
            roc_auc = roc_auc_score(self.y_val, pred_labels)

            mlflow.log_metric("roc_auc", float(roc_auc))
            mlflow.log_metric("f1_score", float(f1))
            mlflow.log_params(params)

        return roc_auc


def train_best_xgb_model(X_train, y_train, best_params):
    train = xgb.DMatrix(X_train, label=y_train)
    model = xgb.train(best_params, train)
    return model


def plot_feature_importance(model, feat_names=None):
    matplotlib.use("Agg")

    fig, ax = plt.subplots(figsize=(10, 8))
    importance_type = "gain"
    if feat_names is not None:
        model.feature_names = list(feat_names)

    xgb.plot_importance(
        model,
        importance_type=importance_type,
        ax=ax,
        title=f"Feature Importance based on {importance_type}",
    )
    plt.tight_layout()
    plt.close(fig)
    return fig


def optuna_tuning(
    X_train,
    y_train,
    X_val,
    y_val,
):
    with mlflow.start_run(
        run_name=f"{MLFLOW_RUNNAME_PREFIX}_{datetime.datetime.now().date()}",
        nested=True,
    ):
        mlflow.set_tag("model", "xgboost")
        mlflow.set_tag("identifier", MLFLOW_RUNNAME_PREFIX)

        xgb_objective = XGBObjective(X_train, y_train, X_val, y_val)
        study_xgb = optuna.create_study(direction="maximize", sampler=sampler)
        study_xgb.optimize(xgb_objective, n_trials=NUM_TRIALS)

        best_params = study_xgb.best_params
        mlflow.log_params(best_params)

        return best_params


def make_predictions(
    model, X_test: pd.DataFrame, preprocessor: ColumnTransformer
) -> np.ndarray:
    X_test = preprocessor.transform(X_test)
    preds = model.predict(xgb.DMatrix(X_test))
    return np.clip(np.rint(preds), 0, 1).astype(int)
