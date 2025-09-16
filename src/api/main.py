import os
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from .inference import ValidationError, validate_and_frame, predict_labels
from .loader import ModelBundle, load_bundle
from .schemas import MetadataResponse, PredictRequest, PredictResponse
from .serving_constants import (
    MLFLOW_TRACKING_URI,
    PREPROCESSOR_MODEL_NAME,
    XGB_MODEL_NAME,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", MLFLOW_TRACKING_URI)
    preprocessor_name = os.getenv("PREPROCESSOR_MODEL_NAME", PREPROCESSOR_MODEL_NAME)
    model_name = os.getenv("XGB_MODEL_NAME", XGB_MODEL_NAME)

    try:
        bundle = load_bundle(
            tracking_uri=tracking_uri,
            preprocessor_name=preprocessor_name,
            model_name=model_name,
        )
        app.state.bundle = bundle
    except Exception as e:
        app.state.bundle = None
        print(f"Failed to load models: {e}")

    yield


app = FastAPI(title="Churn Prediction API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"Status": "OK"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if getattr(app.state, "bundle", None) is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"Status": "READY"}


@app.get("/metadata", response_model=MetadataResponse)
def metadata() -> MetadataResponse:
    bundle: ModelBundle | None = getattr(app.state, "bundle", None)
    if bundle is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return MetadataResponse(
        model=bundle.metadata.get("model", {}),
        preprocessor=bundle.metadata.get("preprocessor", {}),
        feature_order=bundle.feature_order,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    bundle: ModelBundle | None = getattr(app.state, "bundle", None)
    if bundle is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        df = validate_and_frame(body.instances)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        labels = predict_labels(bundle, df)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}") from e

    return PredictResponse(
        predictions=labels,
        model=bundle.metadata.get("model", {}),
        preprocessor=bundle.metadata.get("preprocessor", {}),
        feature_order=bundle.feature_order,
    )
