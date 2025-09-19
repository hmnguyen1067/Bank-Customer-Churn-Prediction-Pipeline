import os

DEFAULT_SEED: int = 42

# Prefect
PREFECT_API_URL: str = os.getenv(
    "PREFECT_API_URL", "http://127.0.0.1:4200/api"
)

# MLflow configuration
MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_NAME: str = "Bank-Customer-Churn-Prediction-Experiment"
MLFLOW_RUNNAME_PREFIX: str = "xgboost_hyperparameter_tuning"

# Evidently
EVIDENTLY_TRACKING_URI: str = os.getenv(
    "EVIDENTLY_TRACKING_URI", "http://localhost:8000"
)
EVIDENTLY_PROJECT: str = "Churn Prediction Project"

DROPPED_COLS: list[str] = ["RowNumber", "CustomerId", "Surname", "Complain"]

CATEGORICAL_FEATURES: list[str] = [
    "Geography",
    "Gender",
    "NumOfProducts",
    "HasCrCard",
    "IsActiveMember",
    "Satisfaction Score",
    "Card Type",
]

NUMERICAL_FEATURES: list[str] = [
    "CreditScore",
    "Age",
    "Tenure",
    "Balance",
    "EstimatedSalary",
    "Point Earned",
]

TARGET: str = "Exited"
PREDICTION_COL: str = "Preds"

# MLFlow registry model names
PREPROCESSOR_MODEL_NAME: str = "ChurnDataPreprocessor"
XGB_MODEL_NAME: str = "XGBoostChurnModel"

NUM_TRIALS = 200

CONNECTION_STRING = "host=localhost port=5434 user=grafana password=grafana"
CONNECTION_STRING_DB = CONNECTION_STRING + " dbname=grafana"

CREATE_TABLE_STATEMENT = """
drop table if exists metrics;
create table metrics(
	timestamp timestamp,
	prediction_drift float,
	num_drifted_columns integer,
	share_missing_values float
)
"""

