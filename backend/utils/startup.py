from urllib.parse import urlsplit, urlunsplit

from backend.config import (
    AUDIO_DIR,
    DATABASE_NAME,
    MODEL_FAKE_CLASS_INDEX,
    MODEL_FAKE_THRESHOLD,
    MODEL_HUMAN_CLASS_INDEX,
    MODEL_LEGACY_ONLY_CNN_WEIGHT,
    MODEL_WEIGHTS_PATH,
    MONGODB_URL,
    SPECTROGRAM_DIR,
    UPLOAD_DIR,
    WAVEFORM_DIR,
)
from backend.utils.audio_conversion import ffmpeg_available, resolve_ffmpeg_binary, resolve_ffprobe_binary


def _redact_url_password(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.password:
        return url
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    username = parsed.username or ""
    netloc = f"{username}:***@{host}" if username else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def build_startup_diagnostics(mongo_ready: bool) -> dict:
    return {
        "mongodb_ready": mongo_ready,
        "mongodb_url": _redact_url_password(MONGODB_URL),
        "database_name": DATABASE_NAME,
        "ffmpeg_ready": ffmpeg_available(),
        "ffmpeg_path": resolve_ffmpeg_binary() or "not found",
        "ffprobe_path": resolve_ffprobe_binary() or "not found",
        "model_weights_path": str(MODEL_WEIGHTS_PATH),
        "model_weights_ready": MODEL_WEIGHTS_PATH.exists(),
        "model_fake_class_index": MODEL_FAKE_CLASS_INDEX,
        "model_human_class_index": MODEL_HUMAN_CLASS_INDEX,
        "model_fake_threshold": MODEL_FAKE_THRESHOLD,
        "model_legacy_only_cnn_weight": MODEL_LEGACY_ONLY_CNN_WEIGHT,
        "upload_dir": str(UPLOAD_DIR),
        "audio_dir": str(AUDIO_DIR),
        "waveform_dir": str(WAVEFORM_DIR),
        "spectrogram_dir": str(SPECTROGRAM_DIR),
    }


def print_startup_diagnostics(diagnostics: dict) -> None:
    print("[startup] EchoGuard diagnostics")
    for key, value in diagnostics.items():
        print(f"[startup] {key}: {value}")
