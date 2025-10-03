# About this repo
End-to-end bank customer churn prediction pipeline with training, registry, serving, and monitoring. High-level product notes are in [docs/PRD.md](docs/PRD.md) and the system design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

# Features
![](assets/BankChurn.png)

- Model Development
  - Jupyter Notebook for exploratory data analysis.
  - Scikit-learn for standardized feature engineering.
  - Xgboost for standard fast, efficient and scalable model.
  - Bayesisan optimization hyperparameter tuning with Optuna.
  - Pytest suite covers data I/O, preprocessing, training/tuning, monitoring glue, and API surfaces.
- Model Evaluation
  - Standard training and holdout datasets to simulate real-world data distribution.
  - MLFlow for detailed experiment tracking and enabling comparison of experiment runs, visualizations and SHAP explanatory plots.
- Model Deployment
  - The models are versioned in MLFlow Model Registry with metadata and dependencies for transparency.
  - FastAPI service loads the latest registered preprocessor/model from MLflow and exposes endpoint for serving.
- Model Monitoring
  - Evidently for automated data drift and prediction performance report
  - Grafana for dashboard visualization of model metrics

# Geting Started
## Prerequisites
- Python >= 3.10, <3.13
- Docker
- Pixi (for a fully reproducible local env)

## Installation
1) Make sure that you have the dataset downloaded
```bash
make data-up
```

2) With Pixi installed, install virtual environment with Pixi
```bash
make env-setup
```

## Usage
### Docker
1) Local stack with Docker (MLflow, MinIO, Postgres, Prefect, Evidently, Grafana, API)
```bash
# Start services
make docker-up

# Run a local Prefect flow that logs runs to MLflow, registers artifacts, creates drift report, and exports metrics.
pixi run python main_flow.py --data-path data/Customer-Churn-Records.csv
```

2) Create a sample request `sample_payload.json`:

```
{
    "instances": [
        {
        "Geography": "France",
        "Gender": "Female",
        "NumOfProducts": 2,
        "HasCrCard": 1,
        "IsActiveMember": 1,
        "Satisfaction Score": 4,
        "Card Type": "Gold",
        "CreditScore": 650,
        "Age": 42,
        "Tenure": 5,
        "Balance": 12345.67,
        "EstimatedSalary": 80000.0,
        "Point Earned": 100.0
        }
    ]
}
```

3) Invoke a POST request to the running API:
```bash
curl -s -X POST http://localhost:8001/predict -H 'Content-Type: application/json' --data @sample_payload.json
```

Note:
- Health/readiness and metadata endpoints: `GET /health`, `GET /ready`, `GET /metadata`.
- Service URLs (defaults): MLflow `:5000`, Prefect `:4200`, Evidently `:8000`, Grafana `:3000`, API `:8001`. See [docs/DOCKER.md](docs/DOCKER.md) for details and overrides.

## Testing
Run all tests:
```bash
# With pixi
pixi run pytest tests -v

# With make
make test
```

## Troubleshooting
- Ports already in use: adjust values in `infra/config/config.env` then `make docker-down && make docker-up`.
- MLflow artifacts error: ensure MinIO is healthy and buckets exist; verify creds in `infra/config/config.env`.
- API `/ready` returns 503: ensure MLflow and MinIO are up, and both preprocessor and model are registered (re-run training flow).

## References
- Data dictionary: [docs/DATA.md](docs/DATA.md)
- Hypothethical product requirements: [docs/PRD.md](docs/PRD.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Docker details: [docs/DOCKER.md](docs/DOCKER.md)
