import argparse

from bank_customer_churn_prediction_pipeline.flow import churn_flow
from bank_customer_churn_prediction_pipeline.constants import (
    DEFAULT_SEED,
    MLFLOW_TRACKING_URI,
    MLFLOW_EXPERIMENT_NAME,
    EVIDENTLY_TRACKING_URI,
    EVIDENTLY_PROJECT,
    NUM_TRIALS,
    MLFLOW_RUNNAME_PREFIX,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Prefect churn prediction flow")
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/Customer-Churn-Records.csv",
        help="Path to Customer-Churn-Records.csv",
    )
    parser.add_argument(
        "--mlflow-uri",
        type=str,
        default=MLFLOW_TRACKING_URI,
        help="MLflow tracking URI",
    )
    parser.add_argument(
        "--experiment",
        type=str,
        default=MLFLOW_EXPERIMENT_NAME,
        help="MLflow experiment name",
    )
    parser.add_argument(
        "--mlflow-run-prefix",
        type=str,
        default=MLFLOW_RUNNAME_PREFIX,
        help="MLflow run name prefix",
    )
    parser.add_argument(
        "--evidently-uri",
        type=str,
        default=EVIDENTLY_TRACKING_URI,
        help="Evidently tracking URI",
    )
    parser.add_argument(
        "--evidently-proj",
        type=str,
        default=EVIDENTLY_PROJECT,
        help="Evidently project name",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=NUM_TRIALS,
        help="Number of Optuna trials",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    churn_flow(
        data_path=args.data_path,
        mlflow_uri=args.mlflow_uri,
        experiment_name=args.experiment,
        runname_prefix=args.mlflow_run_prefix,
        evidently_uri=args.evidently_uri,
        proj_name=args.evidently_proj,
        trials=args.trials,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
