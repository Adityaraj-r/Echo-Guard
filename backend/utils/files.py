import re
from pathlib import Path
from uuid import uuid4


def safe_upload_name(filename: str) -> str:
    stem = Path(filename or "audio").stem
    suffix = Path(filename or "audio.wav").suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "audio"
    return f"{safe_stem}_{uuid4().hex[:10]}{suffix}"


def public_asset_url(path: Path) -> str:
    normalized = path.as_posix()
    marker = "/uploads/"
    if marker in normalized:
        return f"/assets/{normalized.split(marker, 1)[1]}"
    marker = "uploads/"
    if marker in normalized:
        return f"/assets/{normalized.split(marker, 1)[1]}"
    return f"/assets/{path.name}"
