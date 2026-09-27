import re
from pathlib import Path

from backend.config import (
    AUDIO_DIR,
    PROCESSED_DIR,
    SPECTROGRAM_DIR,
    SUPPORTED_EXTENSIONS,
    TEMP_IMAGE_DIR,
    WAVEFORM_DIR,
)

_UPLOAD_STEM = re.compile(r"^.+_[0-9a-f]{10}$")


def _is_within(path: Path, root: Path) -> bool:
    try:
        resolved_path = path.resolve(strict=False)
        resolved_root = root.resolve(strict=False)
        return resolved_path != resolved_root and resolved_root in resolved_path.parents
    except (OSError, RuntimeError):
        return False


def _safe_unlink(path: Path, root: Path) -> bool:
    """Unlink a file only when its containing path is inside a managed root."""
    try:
        if path.is_symlink():
            if path.parent.resolve(strict=False) != root.resolve(strict=False) and not _is_within(
                path.parent, root
            ):
                return False
        elif not _is_within(path, root):
            return False
        if not path.is_file() and not path.is_symlink():
            return False
        path.unlink(missing_ok=True)
        return True
    except (OSError, RuntimeError):
        return False


def _canonical_upload(path: str | Path) -> Path | None:
    candidate = Path(path)
    try:
        if not candidate.is_absolute() or candidate.is_symlink():
            return None
        if candidate.parent.resolve(strict=False) != AUDIO_DIR.resolve(strict=False):
            return None
        if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return None
        if not _UPLOAD_STEM.fullmatch(candidate.stem):
            return None
        return candidate
    except (OSError, RuntimeError):
        return None


def _cleanup_stem(stem: str, original_path: Path | None, include_display: bool) -> None:
    if not _UPLOAD_STEM.fullmatch(stem):
        return
    files = [
        (PROCESSED_DIR / f"{stem}_normalized.wav", AUDIO_DIR),
        (TEMP_IMAGE_DIR / f"model_{stem}_normalized.png", TEMP_IMAGE_DIR),
    ]
    if original_path is not None:
        files.append((original_path, AUDIO_DIR))
    if include_display:
        files.extend(
            [
                (WAVEFORM_DIR / f"{stem}_waveform.png", WAVEFORM_DIR),
                (SPECTROGRAM_DIR / f"{stem}_spectrogram.png", SPECTROGRAM_DIR),
            ]
        )
    for path, root in files:
        _safe_unlink(path, root)


def cleanup_failed_upload(path: str | Path, *, include_display: bool = True) -> None:
    upload = _canonical_upload(path)
    if upload is None:
        return
    _cleanup_stem(upload.stem, upload, include_display)


def cleanup_model_image(path: str | Path) -> None:
    _safe_unlink(Path(path), TEMP_IMAGE_DIR)


def detection_artifact_references(record) -> dict[str, str] | None:
    upload = _upload_from_detection(record)
    if upload is None:
        return None
    stem = upload.stem
    return {
        "uploaded_audio_path": str(upload),
        "converted_wav_path": str(PROCESSED_DIR / f"{stem}_normalized.wav"),
        "waveform_image": f"/assets/waveforms/{stem}_waveform.png",
        "spectrogram_image": f"/assets/spectrograms/{stem}_spectrogram.png",
    }


def _upload_from_detection(record) -> Path | None:
    upload_path = getattr(record, "uploaded_audio_path", None)
    if upload_path:
        return _canonical_upload(upload_path)

    # Backward compatibility for records created before uploaded_audio_path
    # was added: derive the original upload from the normalized file name.
    converted_value = getattr(record, "converted_wav_path", None)
    original_format = str(getattr(record, "original_format", "") or "").lower()
    if not converted_value or f".{original_format}" not in SUPPORTED_EXTENSIONS:
        return None
    converted = Path(converted_value)
    try:
        if not converted.is_absolute() or converted.parent.resolve(strict=False) != PROCESSED_DIR.resolve(
            strict=False
        ):
            return None
        suffix = "_normalized"
        if converted.suffix.lower() != ".wav" or not converted.stem.endswith(suffix):
            return None
        stem = converted.stem[: -len(suffix)]
        upload = AUDIO_DIR / f"{stem}.{original_format}"
        return _canonical_upload(upload)
    except (OSError, RuntimeError):
        return None


def cleanup_detection_files(record) -> None:
    upload = _upload_from_detection(record)
    if upload is None:
        return
    _cleanup_stem(upload.stem, upload, include_display=True)
