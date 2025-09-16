# Docker Guide

This guide explains how to run the local stack (MLflow, MinIO, Postgres, Prefect, Evidently, Grafana) using Docker Compose for development and demos.

## Prerequisites
- Docker Desktop or Docker Engine with Docker Compose v2.21+.
- Make (optional) for convenience targets.

## Quick Start
- Configure env: review and adjust `infra/config/config.env` for ports and credentials.
- Start services: `make docker-up`.
- Stop services: `make docker-down`.
- Without Make:
  - Up: `docker compose -f infra/docker-compose.yaml --env-file infra/config/config.env up -d --build`
  - Down: `docker compose -f infra/docker-compose.yaml down`

## Notes
- The Compose file uses `include` to merge `infra/backend.yaml` and `infra/prefect.yaml`. If your Compose CLI doesn’t support `include`, use this fallback instead:
  - `docker compose -f infra/backend.yaml -f infra/prefect.yaml -f infra/docker-compose.yaml --env-file infra/config/config.env up -d --build`

## Service Endpoints
- MLflow UI: `http://localhost:${MLFLOW_PORT}` (default `5000`)
  - Tracks experiments; serves artifacts to MinIO S3.
- MinIO S3 API: `http://localhost:${MINIO_PORT}` (default `9000`)
- MinIO Console: `http://localhost:${MINIO_CONSOLE_PORT}` (default `9001`)
  - Login with `${MINIO_ROOT_USER}/${MINIO_ROOT_PASSWORD}` (defaults in `config.env`). Buckets `${MLFLOW_BUCKET_NAME}` and `${EVIDENTLY_BUCKET_NAME}` are auto-created.
- Prefect UI: `http://localhost:4200`
- Grafana UI: `http://localhost:3000` (default admin/admin on first login; you will be prompted to change password)
  - A PostgreSQL datasource and dashboards are provisioned from `infra/config` and `infra/dashboards`.
- API: `http://localhost:${API_PORT}` (default `8001`)
  - Endpoints: `/health`, `/ready`, `/metadata`, `/predict`.
- Adminer (DB UI): `http://localhost:8080`
  - Connect to `mlflow_db`, `prefect_db`, or `grafana_db` (server) with the credentials in `config.env`; or connect via host ports below.

## Host Ports and Credentials (defaults)
- MLflow DB (Postgres): `localhost:${MLFLOW_DB_PORT}` (default `5432`), user `mlflow`, password `mlflow`, db `mlflow`.
- Prefect DB (Postgres): `localhost:${PREFECT_DB_PORT}` (default `5433`), user `prefect`, password `prefect`, db `prefect`.
- Grafana DB (Postgres): `localhost:${GRAFANA_DB_PORT}` (default `5434`), user `grafana`, password `grafana`, db `grafana`.
- MinIO S3 API/Console: `localhost:${MINIO_PORT}`/`localhost:${MINIO_CONSOLE_PORT}` (defaults `9000/9001`).
- API: `localhost:${API_PORT}` (default `8001`).

## How It’s Wired
- MLflow server runs with `--serve-artifacts` and stores artifacts in `s3://${MLFLOW_BUCKET_NAME}` via MinIO. S3 credentials come from `MINIO_ACCESS_KEY`/`MINIO_SECRET_ACCESS_KEY` (defaults mapped to the MinIO root creds).
- Two helper jobs create buckets in MinIO if missing: `${MLFLOW_BUCKET_NAME}` and `${EVIDENTLY_BUCKET_NAME}`.
- Evidently service stores its workspace in `s3://${EVIDENTLY_BUCKET_NAME}/workspace` using `s3fs`.
- Grafana connects to the `grafana` Postgres DB; a starter drift dashboard is provisioned from `infra/dashboards/data_drift.json`.

## Run the Pipeline Flow
1) Start the stack: `make docker-up`.
2) Ensure data exists at `data/Customer-Churn-Records.csv` (use `make data` or place manually).
3) Run the flow locally and point it at the Docker services:
   - `python main_flow.py --data-path data/Customer-Churn-Records.csv --mlflow-uri http://localhost:5000 --evidently-uri http://localhost:8000 --trials 50 --seed 42`
4) Explore results:
   - MLflow: experiments, runs, registered models.
   - Evidently: project “Churn Prediction Project” and drift reports.
   - Grafana: “Churn dashboard” showing metrics written by the flow.

## Use the FastAPI Inference API
1) Start the stack: `make docker-up` (builds and runs the `api` service).
2) Ensure the preprocessor and model are registered in MLflow (run the training flow above if needed).
3) Send a sample request:
   - Save as `sample_payload.json`:
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
   - Invoke:
     `curl -s -X POST http://localhost:8001/predict -H 'Content-Type: application/json' --data @sample_payload.json`
4) Health endpoints:
   - `GET http://localhost:8001/health` → process up.
   - `GET http://localhost:8001/ready` → ready when model is loaded (503 otherwise).

## Environment Configuration
- File: `infra/config/config.env`
  - MLflow: `MLFLOW_PORT`, `MLFLOW_DB_*`, `MLFLOW_BUCKET_NAME`.
  - MinIO: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_PORT`, `MINIO_CONSOLE_PORT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_ACCESS_KEY`.
  - Prefect: `PREFECT_DB_*`, `PREFECT_DB_PORT`.
  - Evidently: `EVIDENTLY_BUCKET_NAME`.
  - Grafana DB: `GRAFANA_DB_*`, `GRAFANA_DB_PORT`.
  - API: `API_PORT`.
- Change ports here if something is already in use on your machine.
- If you change bucket names or credentials, update both MinIO creds and the bucket envs; the compose jobs will create missing buckets at startup.

## Common Operations
- Status: `docker compose -f infra/docker-compose.yaml ps`
- Logs (follow): `docker compose -f infra/docker-compose.yaml logs -f mlflow_tracking_server`
- Rebuild a service: `docker compose -f infra/docker-compose.yaml build mlflow_tracking_server`
- Restart a service: `docker compose -f infra/docker-compose.yaml restart grafana`
- Connect to a container: `docker exec -it mlflow_server bash`

## Resetting State
- Stop and remove containers: `make docker-down`
- Remove containers + named volumes (wipe DBs and MinIO data):
  - `docker compose -f infra/docker-compose.yaml down -v`
  - Note: This deletes databases and object storage. Use with care.

## Troubleshooting
- Port already in use: Edit the conflicting port in `infra/config/config.env`, then `make docker-down && make docker-up`.
- Compose error with `include`: Your Compose CLI is too old. Use the fallback with multiple `-f` files (shown above) or upgrade Docker Compose v2.21+.
- MLflow can’t write artifacts: Verify MinIO is healthy; confirm buckets exist in MinIO Console; ensure `MINIO_ACCESS_KEY/MINIO_SECRET_ACCESS_KEY` match MinIO root creds.
- Evidently can’t access S3: Check `FSSPEC_S3_*` envs on the `evidently` service and that MinIO is reachable.
- Grafana shows DB errors: Ensure `grafana_db` is healthy; check logs with `docker compose logs -f grafana_db`.
- Adminer connection: Use server `mlflow_db`/`prefect_db`/`grafana_db` inside the Compose network, or host `localhost` with the mapped ports.
 - API `/ready` returns 503: Ensure MLflow is running, MinIO is healthy, and both preprocessor and model are registered; check `api` logs.
