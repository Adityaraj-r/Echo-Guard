import json
import logging
import os
import shutil
import subprocess
import time
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv.*")
    from pydub import AudioSegment

from backend.config import FFMPEG_PATH, FFPROBE_PATH, MAX_DURATION_SECONDS, TARGET_CHANNELS, TARGET_SAMPLE_RATE

logger = logging.getLogger("echoguard.audio")


class AudioConversionError(RuntimeError):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or message

    def to_payload(self) -> dict:
        return {
            "success": False,
            "error": self.message,
            "details": self.details,
        }


def _candidate_executable(configured_path: str, executable: str) -> str | None:
    configured = (configured_path or "").strip().strip('"')
    exe_name = f"{executable}.exe" if os.name == "nt" else executable

    candidates: list[Path] = []
    if configured:
        path = Path(configured)
        if path.is_dir():
            candidates.append(path / exe_name)
        else:
            candidates.append(path)
            candidates.append(path.parent / exe_name)

    fallback_dir = Path(r"C:\ffmpeg\bin")
    candidates.append(fallback_dir / exe_name)
    if os.name == "nt":
        candidates.extend(_windows_common_candidates(exe_name))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    for path_dir in _system_path_dirs():
        candidate = Path(path_dir) / exe_name
        if candidate.exists():
            return str(candidate.resolve())

    return shutil.which(executable)


def _system_path_dirs() -> list[str]:
    path_values = [os.environ.get("PATH", "")]
    if os.name == "nt":
        try:
            import winreg

            registry_locations = [
                (winreg.HKEY_CURRENT_USER, r"Environment"),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            ]
            for hive, key_path in registry_locations:
                with winreg.OpenKey(hive, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, "Path")
                    path_values.append(value)
        except Exception:
            pass

    dirs: list[str] = []
    for value in path_values:
        for path_dir in value.split(os.pathsep):
            expanded = os.path.expandvars(path_dir.strip())
            if expanded and expanded not in dirs:
                dirs.append(expanded)
    return dirs


def _windows_common_candidates(exe_name: str) -> list[Path]:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    user_profile = os.environ.get("USERPROFILE", "")

    roots = [
        Path(r"C:\ffmpeg\bin"),
        Path(program_files) / "ffmpeg" / "bin",
        Path(program_data) / "chocolatey" / "bin",
        Path(local_app_data) / "Microsoft" / "WinGet" / "Links",
        Path(user_profile) / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links",
    ]
    return [root / exe_name for root in roots if str(root)]


def resolve_ffmpeg_binary() -> str | None:
    return _candidate_executable(FFMPEG_PATH, "ffmpeg")


def resolve_ffprobe_binary() -> str | None:
    return _candidate_executable(FFPROBE_PATH or FFMPEG_PATH, "ffprobe")


def configure_ffmpeg() -> dict:
    ffmpeg = resolve_ffmpeg_binary()
    ffprobe = resolve_ffprobe_binary()

    for binary in (ffmpeg, ffprobe):
        if binary:
            bin_dir = str(Path(binary).parent)
            path_parts = os.environ.get("PATH", "").split(os.pathsep)
            if bin_dir not in path_parts:
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    if ffmpeg:
        AudioSegment.converter = ffmpeg
        AudioSegment.ffmpeg = ffmpeg
    if ffprobe:
        AudioSegment.ffprobe = ffprobe

    diagnostics = {
        "ffmpeg": ffmpeg or "not found",
        "ffprobe": ffprobe or "not found",
        "configured_ffmpeg_path": FFMPEG_PATH,
        "configured_ffprobe_path": FFPROBE_PATH or "(derived from FFMPEG_PATH)",
    }
    print(f"[startup] FFmpeg configuration: {diagnostics}")
    return diagnostics


def validate_ffmpeg_or_raise() -> dict:
    diagnostics = configure_ffmpeg()
    ffmpeg = diagnostics["ffmpeg"]
    ffprobe = diagnostics["ffprobe"]

    if ffmpeg == "not found":
        raise RuntimeError(
            "FFmpeg executable was not found. Set FFMPEG_PATH to the FFmpeg bin folder or ffmpeg.exe path."
        )
    if ffprobe == "not found":
        raise RuntimeError(
            "ffprobe executable was not found. Set FFMPEG_PATH to the FFmpeg bin folder or set FFPROBE_PATH."
        )

    for name, binary in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
        try:
            subprocess.run([binary, "-version"], capture_output=True, text=True, check=True, timeout=8)
        except Exception as exc:
            raise RuntimeError(f"{name} exists but could not be executed: {binary}") from exc

    return diagnostics


def ffmpeg_available() -> bool:
    try:
        validate_ffmpeg_or_raise()
        return True
    except Exception:
        return False


def probe_audio(input_path: Path) -> dict:
    ffprobe = resolve_ffprobe_binary()
    if not ffprobe:
        raise AudioConversionError("Audio metadata probing failed", "ffprobe executable was not found.")

    command = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
    if completed.returncode != 0:
        raise AudioConversionError("Audio metadata probing failed", completed.stderr.strip())
    return json.loads(completed.stdout or "{}")


def convert_to_wav(input_path: str | Path, output_path: str | Path, overwrite: bool = True) -> Path:
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    ffmpeg = resolve_ffmpeg_binary()
    if not ffmpeg:
        raise AudioConversionError(
            "Audio conversion failed",
            "FFmpeg executable was not found. Set FFMPEG_PATH to the FFmpeg bin folder or ffmpeg.exe path.",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-y" if overwrite else "-n",
        "-i",
        str(source),
        "-t",
        str(MAX_DURATION_SECONDS),
        "-vn",
        "-ac",
        str(TARGET_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-sample_fmt",
        "s16",
        str(destination),
    ]

    logger.info("uploaded file path=%s extension=%s", source, source.suffix.lower())
    logger.info("ffmpeg conversion command=%s", " ".join(f'"{part}"' if " " in part else part for part in command))
    logger.info("wav output path=%s", destination)

    started_at = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True)
    elapsed = round(time.perf_counter() - started_at, 3)
    logger.info("ffmpeg conversion duration=%ss", elapsed)

    if completed.returncode != 0:
        logger.error("ffmpeg stderr=%s", completed.stderr.strip())
        raise AudioConversionError("Audio conversion failed", completed.stderr.strip() or "FFmpeg returned a non-zero exit code.")

    if not destination.exists() or destination.stat().st_size == 0:
        raise AudioConversionError("Audio conversion failed", f"Output WAV was not created: {destination}")

    return destination
