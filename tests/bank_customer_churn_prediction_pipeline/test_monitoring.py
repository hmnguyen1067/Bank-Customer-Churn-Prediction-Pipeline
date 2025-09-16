from types import SimpleNamespace

import pandas as pd

import bank_customer_churn_prediction_pipeline.monitoring as mon
from bank_customer_churn_prediction_pipeline.constants import (
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET,
    PREDICTION_COL,
)


def test_create_evidently_data_def_columns(monkeypatch):
    class DD:
        def __init__(self, numerical_columns, categorical_columns):
            self.numerical_columns = numerical_columns
            self.categorical_columns = categorical_columns

    monkeypatch.setattr(mon, "DataDefinition", DD)
    dd = mon.create_evidently_data_def()
    assert dd.numerical_columns == NUMERICAL_FEATURES
    assert dd.categorical_columns == CATEGORICAL_FEATURES + [PREDICTION_COL] + [TARGET]


def test_create_evidently_dataset_wraps_dataframe(monkeypatch):
    calls = {}

    class FakeDataset:
        @classmethod
        def from_pandas(cls, data, data_definition):  # noqa: D401
            calls["data_cols"] = list(data.columns)
            calls["dd"] = data_definition
            return SimpleNamespace(kind="dataset")

    monkeypatch.setattr(mon, "Dataset", FakeDataset)

    df = pd.DataFrame({"a": [1], TARGET: [0]})
    out = mon.create_evidently_dataset(df, df[TARGET], SimpleNamespace())
    assert out.kind == "dataset"
    assert TARGET in calls["data_cols"]


def test_prepare_monitoring_data_adds_prediction_col(monkeypatch):
    def fake_make_predictions(model, X, pp):  # noqa: ARG001
        return [1] * len(X)

    monkeypatch.setattr(mon, "make_predictions", fake_make_predictions)

    X = pd.DataFrame({"a": [1, 2, 3]})
    out = mon.prepare_monitoring_data(X, preprocessor=None, model=None)
    assert PREDICTION_COL in out.columns
    assert out[PREDICTION_COL].tolist() == [1, 1, 1]


def test_generate_evidently_report_calls_run(monkeypatch):
    calls = {}

    class FakeReport:
        def __init__(self, metrics, include_tests=False):  # noqa: ARG002
            self._ran = False

        def run(self, current_data, reference_data):
            calls["ran_with"] = (current_data, reference_data)
            self._ran = True
            return self

        def dict(self):  # minimal metrics structure
            return {
                "metrics": [
                    {"value": 0.1},
                    {"value": {"count": 3}},
                    {"value": {"share": 0.2}},
                ]
            }

    monkeypatch.setattr(mon, "Report", FakeReport)

    cur = SimpleNamespace()
    ref = SimpleNamespace()
    report = mon.generate_evidently_report(cur, ref)
    assert isinstance(report, FakeReport)
    assert calls.get("ran_with") == (cur, ref)


def test_upload_report_uses_workspace_when_project_exists(monkeypatch):
    calls = {}

    class FakeWS:
        def __init__(self, uri):  # noqa: D401
            calls["uri"] = uri

        def search_project(self, name):  # noqa: D401
            return [SimpleNamespace(id="123")]

        def get_project(self, pid):  # noqa: D401
            calls["get_project"] = pid
            return SimpleNamespace(id=pid)

        def add_run(self, pid, report):  # noqa: D401
            calls["add_run"] = (pid, report)

    monkeypatch.setattr(mon, "RemoteWorkspace", FakeWS)
    mon.upload_report(SimpleNamespace(), evidently_uri="http://ws", proj_name="P")
    assert calls["uri"] == "http://ws"
    assert calls["get_project"] == "123"
    assert calls["add_run"][0] == "123"


def test_upload_report_creates_project_when_missing(monkeypatch):
    calls = {}

    class FakeWS:
        def __init__(self, uri):  # noqa: D401
            pass

        def search_project(self, name):  # noqa: D401
            return []

        def create_project(self, name):  # noqa: D401
            calls["created"] = name
            return SimpleNamespace(id="NEW")

        def add_run(self, pid, report):  # noqa: D401
            calls["add_run"] = (pid, report)

    monkeypatch.setattr(mon, "RemoteWorkspace", FakeWS)
    mon.upload_report(SimpleNamespace(), evidently_uri="http://ws", proj_name="N")
    assert calls["created"] == "N"
    assert calls["add_run"][0] == "NEW"


def test_insert_metrics_to_db_executes_sql(monkeypatch):
    # metrics structure expected by insert_metrics_to_db
    metrics = [
        {"value": 0.1},
        {"value": {"count": 3}},
        {"value": {"share": 0.2}},
    ]

    calls = {"executed": []}

    class FakeCursor:
        def execute(self, sql, params):
            calls["executed"].append((sql, params))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401
            return False

    class FakeConn:
        def __init__(self, *a, **k):  # noqa: D401, ARG002
            pass

        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401
            return False

    class FakePsycopg:
        def connect(self, *a, **k):  # noqa: D401, ARG002
            return FakeConn()

    # Patch psycopg module in monitoring
    monkeypatch.setattr(mon, "psycopg", FakePsycopg())

    mon.insert_metrics_to_db(metrics)
    assert len(calls["executed"]) == 1
    sql, params = calls["executed"][0]
    assert "insert into metrics" in sql.lower()
    assert len(params) == 4
