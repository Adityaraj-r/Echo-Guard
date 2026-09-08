import time
import logging
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from fastapi import UploadFile
from pydub import AudioSegment

from backend.config import (
    AUDIO_DIR,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_SIZE_MB,
    PROCESSED_DIR,
    SPECTROGRAM_DIR,
    SUPPORTED_EXTENSIONS,
    TARGET_CHANNELS,
    TARGET_SAMPLE_RATE,
    WAVEFORM_DIR,
)
from backend.preprocessing.audio_io import load_audio_fast
from backend.utils.audio_conversion import AudioConversionError, convert_to_wav, probe_audio
from backend.utils.files import public_asset_url, safe_upload_name
from backend.visualization.spectrogram import create_forensic_spectrogram
from backend.visualization.waveform import create_waveform_image

logger = logging.getLogger("echoguard.audio.pipeline")


class AudioPipelineError(ValueError):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or message

    def to_payload(self) -> dict:
        return {"success": False, "error": self.message, "details": self.details}


async def persist_upload(upload: UploadFile) -> Path:
    filename = safe_upload_name(upload.filename or "recording.webm")
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise AudioPipelineError(f"Unsupported audio format '{Path(filename).suffix}'. Supported formats: {supported}.")

    destination = AUDIO_DIR / filename
    bytes_written = 0
    with destination.open("wb") as buffer:
        while chunk := upload.file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                buffer.close()
                destination.unlink(missing_ok=True)
                raise AudioPipelineError(
                    "Uploaded audio file is too large.",
                    f"Maximum upload size is {MAX_UPLOAD_SIZE_MB} MB.",
                )
            buffer.write(chunk)
    logger.info(
        "persisted upload filename=%s content_type=%s bytes=%s path=%s",
        filename,
        upload.content_type,
        bytes_written,
        destination,
    )
    return destination


def validate_audio_file(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise AudioPipelineError(f"Unsupported audio format '{path.suffix}'. Supported formats: {supported}.")
    if path.stat().st_size == 0:
        raise AudioPipelineError("Uploaded audio file is empty.")
    logger.info("validating audio path=%s extension=%s bytes=%s", path, path.suffix.lower(), path.stat().st_size)


def convert_to_normalized_wav(source_path: Path) -> Path:
    try:
        normalized_path = PROCESSED_DIR / f"{source_path.stem}_normalized.wav"
        return convert_to_wav(source_path, normalized_path, overwrite=True)
    except AudioConversionError as exc:
        raise AudioPipelineError(exc.message, exc.details) from exc


def extract_metadata(original_path: Path, wav_path: Path) -> dict:
    probe = {}
    try:
        probe = probe_audio(original_path)
    except AudioConversionError:
        probe = {}

    audio = AudioSegment.from_file(wav_path)
    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    bitrate = fmt.get("bit_rate") or audio_stream.get("bit_rate")
    bitrate_kbps = round(int(bitrate) / 1000) if str(bitrate or "").isdigit() else None

    return {
        "duration": round(len(audio) / 1000, 2),
        "sample_rate": audio.frame_rate,
        "bitrate": bitrate_kbps,
        "channels": audio.channels,
        "codec": audio_stream.get("codec_name") or original_path.suffix.lower().lstrip(".") or "unknown",
        "file_size": original_path.stat().st_size,
        "normalized_format": "wav",
        "source_format": fmt.get("format_name") or original_path.suffix.lower().lstrip("."),
    }


def generate_waveform_data(wav_path: Path, points: int = 512) -> list[float]:
    samples, _ = load_audio_fast(wav_path, TARGET_SAMPLE_RATE, mono=True)
    if samples.size == 0:
        return []

    chunk_size = max(1, int(np.ceil(samples.size / points)))
    remainder = samples.size % chunk_size
    if remainder:
        samples = np.pad(samples, (0, chunk_size - remainder))
    chunks = samples.reshape(-1, chunk_size)
    peaks = np.max(np.abs(chunks), axis=1)
    max_peak = float(np.max(peaks)) or 1.0
    return [round(float(value / max_peak), 4) for value in peaks[:points]]


def process_audio(original_path: Path) -> dict:
    started_at = time.perf_counter()
    validate_audio_file(original_path)
    wav_path = convert_to_normalized_wav(original_path)

    # Re-save through librosa + soundfile so upload and recorder inputs both
    # reach inference as mono 16 kHz PCM WAV tensors.
    y, sr = librosa.load(wav_path, sr=TARGET_SAMPLE_RATE, mono=True)
    if y.size == 0:
        raise AudioPipelineError("Uploaded audio contains no decodable samples.")
    if not np.isfinite(y).all():
        logger.warning("non-finite samples detected path=%s; replacing with zeros", wav_path)
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)

    input_peak = float(np.max(np.abs(y))) if y.size else 0.0
    if input_peak > 0:
        y = np.clip(y / input_peak, -1.0, 1.0).astype(np.float32)
    else:
        raise AudioPipelineError("Uploaded audio is silent after decoding.")

    sf.write(wav_path, y, sr, subtype="PCM_16")
    logger.info(
        "normalized waveform path=%s duration=%.3fs sample_rate=%s channels=%s input_peak=%.6f output_peak=%.6f subtype=PCM_16",
        wav_path,
        y.size / sr if sr else 0,
        sr,
        TARGET_CHANNELS,
        input_peak,
        float(np.max(np.abs(y))) if y.size else 0.0,
    )

    spectrogram_path = SPECTROGRAM_DIR / f"{original_path.stem}_spectrogram.png"
    waveform_image_path = WAVEFORM_DIR / f"{original_path.stem}_waveform.png"
    create_forensic_spectrogram(wav_path, spectrogram_path, TARGET_SAMPLE_RATE)
    create_waveform_image(wav_path, waveform_image_path, TARGET_SAMPLE_RATE)
    metadata = extract_metadata(original_path, wav_path)
    logger.info(
        "audio metadata filename=%s duration=%ss sample_rate=%s channels=%s normalized_format=%s source_format=%s",
        original_path.name,
        metadata.get("duration"),
        metadata.get("sample_rate"),
        metadata.get("channels"),
        metadata.get("normalized_format"),
        metadata.get("source_format"),
    )

    return {
        "original_path": original_path,
        "normalized_path": wav_path,
        "original_format": original_path.suffix.lower().lstrip("."),
        "spectrogram_path": spectrogram_path,
        "spectrogram_url": public_asset_url(spectrogram_path),
        "waveform_image_path": waveform_image_path,
        "waveform_image_url": public_asset_url(waveform_image_path),
        "waveform": generate_waveform_data(wav_path),
        "metadata": metadata,
        "processing_time": round(time.perf_counter() - started_at, 3),
    }
