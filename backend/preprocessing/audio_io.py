from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def load_audio_fast(path: str | Path, target_sr: int, mono: bool = True) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=False, dtype="float32")
    if data.ndim == 2 and mono:
        data = data.mean(axis=1)
    elif data.ndim == 2:
        data = data[:, 0]

    if sr != target_sr and data.size:
        gcd = np.gcd(sr, target_sr)
        data = resample_poly(data, target_sr // gcd, sr // gcd).astype(np.float32)
        sr = target_sr

    return np.asarray(data, dtype=np.float32), sr
