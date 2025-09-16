import numpy as np
import pandas as pd

import bank_customer_churn_prediction_pipeline.flow as fl


def test_load_data_task_calls_split_data(monkeypatch, sample_df):
    calls = {}

    def fake_read_data(p):  # noqa: D401, ARG001
        return sample_df

    def fake_split_data(df, seed):  # noqa: D401, ARG001
        calls["split"] = True
        return ("Xtr", "ytr", "Xv", "yv", "Xt", "yt")

    monkeypatch.setattr(fl, "read_data", fake_read_data)
    monkeypatch.setattr(fl, "split_data", fake_split_data)

    out = fl.load_data.fn("/path.csv", seed=123)
    assert calls.get("split") is True
    assert out == ("Xtr", "ytr", "Xv", "yv", "Xt", "yt")


def test_preprocess_task_delegates(monkeypatch):
    def fake_preprocess_data(X_tr, X_val):  # noqa: D401, ARG001
        return ("Xtr_tf", "Xval_tf", ["f1", "f2"])

    monkeypatch.setattr(fl, "preprocess_data", fake_preprocess_data)
    out = fl.preprocess.fn("Xtr", "Xval")
    assert out == ("Xtr_tf", "Xval_tf", ["f1", "f2"])


def test_hyperparameter_tuning_task_delegates(monkeypatch):
    def fake_optuna_tuning(*a, **k):  # noqa: D401, ARG002
        return {"n_estimators": 5}

    monkeypatch.setattr(fl, "optuna_tuning", fake_optuna_tuning)
    out = fl.hyperparameter_tuning.fn(
        "Xtr", "ytr", "Xval", "yval", runname_prefix="r", n_trials=1
    )
    assert out == {"n_estimators": 5}


def test_load_registered_artifacts_task(monkeypatch):
    class P:  # noqa: D401
        pass

    class M:  # noqa: D401
        pass

    import mlflow

    monkeypatch.setattr(mlflow.sklearn, "load_model", lambda *a, **k: P())
    monkeypatch.setattr(mlflow.xgboost, "load_model", lambda *a, **k: M())

    pp, model = fl.load_registered_artifacts.fn()
    assert isinstance(pp, P)
    assert isinstance(model, M)


def test_create_drift_report_pipeline(monkeypatch):
    calls = {}

    def fake_data_def():  # noqa: D401
        return "dd"

    def fake_prep(X, pp, m):  # noqa: D401, ARG001
        return X.assign(Preds=0)

    def fake_dataset(X, y, dd):  # noqa: D401, ARG001
        return (X, y, dd)

    class Report:
        def dict(self):
            return {"metrics": [1, 2, 3]}

    def fake_report(cur, ref):  # noqa: D401, ARG001
        return Report()

    def fake_upload(report, uri, proj):  # noqa: D401, ARG001
        calls["uploaded"] = True

    monkeypatch.setattr(fl, "create_evidently_data_def", fake_data_def)
    monkeypatch.setattr(fl, "prepare_monitoring_data", fake_prep)
    monkeypatch.setattr(fl, "create_evidently_dataset", fake_dataset)
    monkeypatch.setattr(fl, "generate_evidently_report", fake_report)
    monkeypatch.setattr(fl, "upload_report", fake_upload)

    X_tr = pd.DataFrame({"a": [1, 2]})
    y_tr = np.array([0, 1])
    X_t = pd.DataFrame({"a": [3, 4]})
    y_t = np.array([1, 0])
    metrics = fl.create_drift_report.fn(
        X_tr,
        y_tr,
        X_t,
        y_t,
        preprocessor=None,
        model=None,
        evidently_uri="u",
        proj_name="p",
    )
    assert metrics == [1, 2, 3]
    assert calls.get("uploaded") is True


def test_grafana_monitor_delegates(monkeypatch):
    calls = {"db": False, "ins": False}

    def fake_create_db():  # noqa: D401
        calls["db"] = True

    def fake_insert(metrics):  # noqa: D401, ARG001
        calls["ins"] = True

    monkeypatch.setattr(fl, "create_db", fake_create_db)
    monkeypatch.setattr(fl, "insert_metrics_to_db", fake_insert)

    fl.grafana_monitor.fn([1, 2])
    assert calls["db"] and calls["ins"]
