from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    instances: List[Dict[str, Any]] = Field(..., description="List of records")


class PredictResponse(BaseModel):
    predictions: List[int]
    model: Dict[str, Any]
    preprocessor: Dict[str, Any]
    feature_order: List[str]


class MetadataResponse(BaseModel):
    model: Dict[str, Any]
    preprocessor: Dict[str, Any]
    feature_order: List[str]
