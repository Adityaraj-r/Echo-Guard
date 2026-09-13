import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"
API_TITLE = os.getenv("API_TITLE", "EchoGuard API")
API_VERSION = os.getenv("API_VERSION", "2.0.0")


def _csv_env(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "echoguard")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "")
FFPROBE_PATH = os.getenv("FFPROBE_PATH", "")


def _default_model_weights_path() -> Path:
    candidates = [
        BASE_DIR / "echoguard_weights.pth",
        BASE_DIR.parent / "echoguard_weights.pth",
    ]
    return next((path for path in candidates if path.exists()), candidates[0])


MODEL_WEIGHTS_PATH = Path(os.getenv("MODEL_WEIGHTS_PATH", _default_model_weights_path())).resolve()
MODEL_FAKE_CLASS_INDEX = int(os.getenv("MODEL_FAKE_CLASS_INDEX", "0"))
MODEL_HUMAN_CLASS_INDEX = int(os.getenv("MODEL_HUMAN_CLASS_INDEX", os.getenv("MODEL_REAL_CLASS_INDEX", "1")))
MODEL_FAKE_THRESHOLD = float(os.getenv("MODEL_FAKE_THRESHOLD", "0.65"))
MODEL_HUMAN_THRESHOLD = float(os.getenv("MODEL_HUMAN_THRESHOLD", "0.35"))
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "2.5"))
MODEL_FUSION_CNN_WEIGHT = float(os.getenv("MODEL_FUSION_CNN_WEIGHT", "0.35"))
MODEL_LEGACY_ONLY_CNN_WEIGHT = float(os.getenv("MODEL_LEGACY_ONLY_CNN_WEIGHT", "0.2"))
ENHANCED_MODEL_WEIGHTS_PATH = Path(os.getenv("ENHANCED_MODEL_WEIGHTS_PATH", BASE_DIR / "echoguard_hybrid_weights.pth")).resolve()
CALIBRATION_PATH = Path(os.getenv("CALIBRATION_PATH", BASE_DIR / "calibration.json")).resolve()

CORS_ORIGINS = _csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS", "*")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
AUDIO_DIR = UPLOAD_DIR / "audio"
WAVEFORM_DIR = UPLOAD_DIR / "waveforms"
SPECTROGRAM_DIR = UPLOAD_DIR / "spectrograms"
PROCESSED_DIR = AUDIO_DIR / "converted"

TEMP_AUDIO_DIR = Path(os.getenv("TEMP_AUDIO_DIR", BASE_DIR / "temp_audio")).resolve()
TEMP_IMAGE_DIR = Path(os.getenv("TEMP_IMAGE_DIR", BASE_DIR / "temp_images")).resolve()


MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

SUPPORTED_EXTENSIONS = {
    ".wav",
    ".aac",
    ".m4a",
    ".flac",
    ".mp3",
    ".aiff",
    ".aif",
    ".ogg",
    ".wma",
    ".dsf",
    ".dff",
    ".webm",
}


def ensure_directories() -> None:
    for path in (UPLOAD_DIR, AUDIO_DIR, WAVEFORM_DIR, SPECTROGRAM_DIR, PROCESSED_DIR, TEMP_AUDIO_DIR, TEMP_IMAGE_DIR):
        path.mkdir(parents=True, exist_ok=True)
