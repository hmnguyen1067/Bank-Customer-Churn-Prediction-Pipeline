from fastapi.testclient import TestClient

from api.main import app as fastapi_app
from api.serving_constants import CATEGORICAL_FEATURES, NUMERICAL_FEATURES


def _valid_record():
    rec = {
        **{c: "A" for c in CATEGORICAL_FEATURES},
        **{n: 1 for n in NUMERICAL_FEATURES},
    }
    return rec


def test_health_ok():
    with TestClient(fastapi_app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"Status": "OK"}


def test_ready_not_loaded_503():
    with TestClient(fastapi_app) as client:
        fastapi_app.state.bundle = None
        r = client.get("/ready")
        assert r.status_code == 503


def test_ready_loaded_ready():
    with TestClient(fastapi_app) as client:
        fastapi_app.state.bundle = object()
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json() == {"Status": "READY"}


def test_metadata_503_when_not_loaded():
    with TestClient(fastapi_app) as client:
        fastapi_app.state.bundle = None
        r = client.get("/metadata")
        assert r.status_code == 503


def test_metadata_happy_path_returns_metadata(monkeypatch):
    class DummyBundle:
        def __init__(self):
            self.metadata = {
                "model": {"name": "X", "version": 1},
                "preprocessor": {"name": "P", "version": 2},
            }
            self.feature_order = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)

    with TestClient(fastapi_app) as client:
        fastapi_app.state.bundle = DummyBundle()
        r = client.get("/metadata")
        assert r.status_code == 200
        body = r.json()
        assert body["model"]["name"] == "X"
        assert body["preprocessor"]["version"] == 2
        assert body["feature_order"] == list(CATEGORICAL_FEATURES) + list(
            NUMERICAL_FEATURES
        )


def test_predict_validation_errors_422():
    with TestClient(fastapi_app) as client:
        fastapi_app.state.bundle = object()
        rec = _valid_record()
        rec.pop(next(iter(CATEGORICAL_FEATURES)))
        r = client.post("/predict", json={"instances": [rec]})
        assert r.status_code == 422


def test_predict_success(monkeypatch):
    import api.main as api_main

    def fake_predict_labels(bundle, df):  # noqa: ARG001
        return [0] * len(df)

    monkeypatch.setattr(api_main, "predict_labels", fake_predict_labels)

    class DummyBundle:
        def __init__(self):
            self.metadata = {
                "model": {"name": "X", "version": 1},
                "preprocessor": {"name": "P", "version": 2},
            }
            self.feature_order = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)

    with TestClient(fastapi_app) as client:
        fastapi_app.state.bundle = DummyBundle()
        instances = [_valid_record(), _valid_record()]
        r = client.post("/predict", json={"instances": instances})
        assert r.status_code == 200
        body = r.json()
        assert body["predictions"] == [0, 0]
        assert body["model"]["name"] == "X"
        assert body["feature_order"] == list(CATEGORICAL_FEATURES) + list(
            NUMERICAL_FEATURES
        )
