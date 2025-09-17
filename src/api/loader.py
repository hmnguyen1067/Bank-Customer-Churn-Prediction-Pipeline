from dataclasses import dataclass
from typing import Any, Dict, Optional

import mlflow
from mlflow.tracking import MlflowClient

from .serving_constants import (CATEGORICAL_FEATURES, MLFLOW_TRACKING_URI,
                                NUMERICAL_FEATURES, PREPROCESSOR_MODEL_NAME,
                                XGB_MODEL_NAME)


@dataclass
class ModelBundle:
    preprocessor: Any
    model: Any
    feature_order: list[str]
    metadata: Dict[str, Any]


def _get_latest_version(client: MlflowClient, name: str) -> Optional[int]:
    try:
        versions = client.search_model_versions(f"name='{name}'")
        if not versions:
            return None
        return max(int(v.version) for v in versions)
    except Exception:
        return None


def load_bundle(
    tracking_uri: Optional[str] = None,
    preprocessor_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> ModelBundle:
    mlflow.set_tracking_uri(tracking_uri or MLFLOW_TRACKING_URI)

    preprocessor_name = preprocessor_name or PREPROCESSOR_MODEL_NAME
    model_name = model_name or XGB_MODEL_NAME

    preprocessor = mlflow.sklearn.load_model(f"models:/{preprocessor_name}/latest")
    model = mlflow.xgboost.load_model(f"models:/{model_name}/latest")

    client = MlflowClient()
    preprocessor_version = _get_latest_version(client, preprocessor_name)
    model_version = _get_latest_version(client, model_name)

    feature_order = list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)

    metadata = {
        "preprocessor": {"name": preprocessor_name, "version": preprocessor_version},
        "model": {"name": model_name, "version": model_version},
        "feature_order": feature_order,
    }

    return ModelBundle(
        preprocessor=preprocessor,
        model=model,
        feature_order=feature_order,
        metadata=metadata,
    )
