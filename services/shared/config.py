from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "echoguard"
    environment: str = "local"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    redis_url: str = "redis://redis:6379/0"
    database_url: str = "postgresql+psycopg://echoguard:echoguard@postgres:5432/echoguard"
    model_service_url: str = "http://model-service:9000"

    upload_dir: Path = Path("/data/uploads")
    stream_dir: Path = Path("/data/streams")
    audio_jobs_stream: str = "audio_jobs"
    failed_jobs_stream: str = "audio_jobs_failed"
    consumer_group: str = "audio-workers"

    cache_ttl_seconds: int = 60 * 60 * 24
    rate_limit_per_minute: int = 60
    max_retries: int = 3

    sample_rate: int = 22050
    duration_seconds: float = 5.0
    n_mels: int = 128
    n_fft: int = 2048
    hop_length: int = 512

    model_path: str = "/models/echoguard.onnx"
    torch_weights_path: str = "/models/echoguard_weights.pth"
    use_gpu: bool = True

    def __init__(self, **data):
        super().__init__(**data)
        # Support local environment - check if weights exist in root directory
        local_weights = Path(__file__).parent.parent.parent / "echoguard_weights.pth"
        if local_weights.exists():
            self.torch_weights_path = str(local_weights)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
