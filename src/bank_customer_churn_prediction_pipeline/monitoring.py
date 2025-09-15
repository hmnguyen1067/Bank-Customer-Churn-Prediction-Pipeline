from constants import (
    EVIDENTLY_TRACKING_URI,
    NUMERICAL_FEATURES,
    CATEGORICAL_FEATURES,
    TARGET,
    PREDICTION_COL,
    EVIDENTLY_PROJECT,
)
from evidently import Report, DataDefinition, Dataset
from evidently.presets import DataDriftPreset
from evidently.ui.workspace import RemoteWorkspace
from evidently.metrics import ValueDrift, DriftedColumnsCount, MissingValueCount

from training import make_predictions


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


def upload_report(report: Report):
    ws = RemoteWorkspace(EVIDENTLY_TRACKING_URI)

    if proj_list := ws.search_project(EVIDENTLY_PROJECT):
        proj_id = proj_list[0].id
        project = ws.get_project(proj_id)
    else:
        project = ws.create_project(EVIDENTLY_PROJECT)

    ws.add_run(project.id, report)
