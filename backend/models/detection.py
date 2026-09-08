from datetime import datetime
from typing import Any, Optional

from beanie import Document, Indexed
from pydantic import Field


class Detection(Document):
    filename: str
    original_format: Optional[str] = None
    converted_wav_path: Optional[str] = None
    waveform_image: Optional[str] = None
    spectrogram_image: Optional[str] = None
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    uploaded_at: Indexed(datetime) = Field(default_factory=datetime.utcnow)
    processing_time: Optional[float] = None
    is_live_recording: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"

    class Settings:
        name = "detections"
        indexes = ["filename", "prediction", "status", "-uploaded_at"]
