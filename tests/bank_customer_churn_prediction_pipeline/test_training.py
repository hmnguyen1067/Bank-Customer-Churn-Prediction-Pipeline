import numpy as np
import matplotlib.figure

import bank_customer_churn_prediction_pipeline.training as tr


def _stub_xgb(monkeypatch):
    class DummyDMatrix:
        def __init__(self, data, label=None):  # noqa: D401
            try:
                self.n = len(data)
            except Exception:  # noqa: BLE001
                self.n = 1
            self.label = label

    class DummyModel:
        def __init__(self, out=0.0):
            self._out = out

        def predict(self, dmat):
            import numpy as _np

            return _np.full(getattr(dmat, "n", 1), self._out, dtype=float)

    def fake_train(
        params, dtrain, evals=None, early_stopping_rounds=None, verbose_eval=None
    ):  # noqa: ARG001
        return DummyModel(out=0.0)

    monkeypatch.setattr(tr.xgb, "DMatrix", DummyDMatrix)
    monkeypatch.setattr(tr.xgb, "train", fake_train)

    return DummyDMatrix, DummyModel


def test_xgb_objective_returns_float_and_logs(monkeypatch):
    DummyDMatrix, DummyModel = _stub_xgb(monkeypatch)

    # Build small synthetic arrays
    X_train = np.zeros((10, 3))
    y_train = np.array([0, 1] * 5)
    X_val = np.zeros((6, 3))
    y_val = np.array([0, 1, 0, 1, 0, 1])

    obj = tr.XGBObjective(X_train, y_train, X_val, y_val, seed=42)

    class FakeTrial:
        def suggest_int(self, *a, **k):  # noqa: D401, ARG002
            return 10

        def suggest_float(self, *a, **k):  # noqa: D401, ARG002
            return 0.1

    val = obj(FakeTrial())
    assert isinstance(val, float)
    assert 0.0 <= val <= 1.0


def test_train_best_xgb_model_invokes_xgb_train(monkeypatch):
    calls = {}

    class DummyDMatrix:
        def __init__(self, data, label=None):  # noqa: D401
            calls["dmatrix"] = True

    class DummyModel:  # noqa: D401
        pass

    def fake_train(params, dtrain):  # noqa: ARG001
        calls["params"] = params
        return DummyModel()

    monkeypatch.setattr(tr.xgb, "DMatrix", DummyDMatrix)
    monkeypatch.setattr(tr.xgb, "train", fake_train)

    model = tr.train_best_xgb_model(
        np.zeros((5, 2)), np.array([0, 1, 0, 1, 0]), {"n_estimators": 10}
    )
    assert isinstance(model, DummyModel)
    assert calls.get("dmatrix") is True
    assert calls.get("params") == {"n_estimators": 10}


def test_plot_feature_importance_returns_figure(monkeypatch):
    class DummyModel:  # noqa: D401
        pass

    def fake_plot_importance(model, importance_type, ax, title):  # noqa: ARG001
        ax.bar([0, 1], [1, 2])

    monkeypatch.setattr(tr.xgb, "plot_importance", fake_plot_importance)

    fig = tr.plot_feature_importance(DummyModel(), feat_names=["f1", "f2"])
    assert isinstance(fig, matplotlib.figure.Figure)


def test_make_predictions_rounds_and_clips(monkeypatch):
    class DummyModel:
        def predict(self, dmat):
            import numpy as _np

            # produce values that round/clip to [1, 0, 1]
            return _np.array([0.6, -0.4, 1.7])

    class DummyPreproc:
        def transform(self, X):
            return np.asarray([[0], [0], [0]])

    out = tr.make_predictions(DummyModel(), np.zeros((3, 2)), DummyPreproc())
    assert out.tolist() == [1, 0, 1]


def test_optuna_tuning_uses_study_and_logs(monkeypatch, mlflow_noop):
    class FakeStudy:
        def __init__(self):
            self.best_params = {"n_estimators": 123}

        def optimize(self, objective, n_trials):  # noqa: ARG002
            class T:
                def suggest_int(self, *a, **k):
                    return 10

                def suggest_float(self, *a, **k):
                    return 0.1

            objective(T())

    monkeypatch.setattr(
        tr.optuna, "create_study", lambda direction, sampler: FakeStudy()
    )

    # Minimal arrays
    X_train = np.zeros((4, 2))
    y_train = np.array([0, 1, 0, 1])
    X_val = np.zeros((2, 2))
    y_val = np.array([0, 1])

    # Stub xgb internals used by XGBObjective
    _stub_xgb(monkeypatch)

    params = tr.optuna_tuning(
        X_train, y_train, X_val, y_val, runname_prefix="t", n_trials=1
    )
    assert params == {"n_estimators": 123}
