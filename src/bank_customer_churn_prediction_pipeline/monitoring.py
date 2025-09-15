from .constants import (
    EVIDENTLY_TRACKING_URI,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    TARGET,
    PREDICTION_COL,
    EVIDENTLY_PROJECT,
    CONNECTION_STRING,
    CONNECTION_STRING_DB,
    CREATE_TABLE_STATEMENT,
)
from evidently import Report, DataDefinition, Dataset
from evidently.presets import DataDriftPreset
from evidently.ui.workspace import RemoteWorkspace
from evidently.metrics import ValueDrift, DriftedColumnsCount, MissingValueCount
import psycopg
import datetime

from .training import make_predictions


def create_evidently_data_def():
    data_definition = DataDefinition(
        numerical_columns=NUMERICAL_FEATURES,
        categorical_columns=CATEGORICAL_FEATURES + [PREDICTION_COL] + [TARGET],
    )
    return data_definition


def create_evidently_dataset(X, y, data_definition: DataDefinition):
    return Dataset.from_pandas(
        data=X.assign(**{TARGET: y}),
        data_definition=data_definition,
    )


def prepare_monitoring_data(X, preprocessor, model):
    preds = make_predictions(model, X, preprocessor)
    return X.assign(**{PREDICTION_COL: preds})


def generate_evidently_report(
    current_data: Dataset,
    reference_data: Dataset,
) -> Report:
    report = Report(
        [
            ValueDrift(column=PREDICTION_COL),
            DriftedColumnsCount(),
            MissingValueCount(column=PREDICTION_COL),
            DataDriftPreset(),
        ],
        include_tests=True,
    )

    report = report.run(current_data, reference_data=reference_data)
    return report


def upload_report(
    report: Report, evidently_uri=EVIDENTLY_TRACKING_URI, proj_name=EVIDENTLY_PROJECT
):
    ws = RemoteWorkspace(evidently_uri)

    if proj_list := ws.search_project(proj_name):
        proj_id = proj_list[0].id
        project = ws.get_project(proj_id)
    else:
        project = ws.create_project(proj_name)

    ws.add_run(project.id, report)


def create_db():
    with psycopg.connect(CONNECTION_STRING, autocommit=True) as conn:
        res = conn.execute("SELECT 1 FROM pg_database WHERE datname='grafana'")
        if len(res.fetchall()) == 0:
            conn.execute("create database grafana;")
        with psycopg.connect(CONNECTION_STRING_DB) as conn:
            conn.execute(CREATE_TABLE_STATEMENT)


def insert_metrics_to_db(metrics):
    prediction_drift, num_drifted_columns, share_missing_values = (
        metrics[0]["value"],
        metrics[1]["value"]["count"],
        metrics[2]["value"]["share"],
    )

    with psycopg.connect(CONNECTION_STRING_DB, autocommit=True) as conn:
        with conn.cursor() as curr:
            curr.execute(
                "insert into metrics(timestamp, prediction_drift, num_drifted_columns, share_missing_values) values (%s, %s, %s, %s)",
                (
                    datetime.datetime.now(),
                    prediction_drift,
                    num_drifted_columns,
                    share_missing_values,
                ),
            )
