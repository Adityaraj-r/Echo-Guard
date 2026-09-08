from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"


class Prediction(BaseModel):
    verdict: str
    confidence: float = Field(ge=0.0, le=100.0)
    fake_probability: float = Field(ge=0.0, le=1.0)
    human_probability: float = Field(ge=0.0, le=1.0)
    risk_level: str
    synthetic_probability: float = Field(ge=0.0, le=1.0)
    authentic_probability: float = Field(ge=0.0, le=1.0)
    model_version: str = "unknown"


class JobCreated(BaseModel):
    job_id: str
    status: JobStatus
    cached: bool = False


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    filename: str | None = None
    audio_hash: str | None = None
    prediction: Prediction | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ModelPredictionRequest(BaseModel):
    job_id: str
    spectrogram: list[list[list[float]]]


class BatchPredictionRequest(BaseModel):
    items: list[ModelPredictionRequest]


class BatchPredictionResponse(BaseModel):
    predictions: dict[str, Prediction]
