from pathlib import Path

import numpy as np
from scipy import signal
from scipy.fftpack import dct

from backend.config import TARGET_SAMPLE_RATE
from backend.preprocessing.audio_io import load_audio_fast


def _resize_time(matrix: np.ndarray, frames: int = 256) -> np.ndarray:
    if matrix.shape[1] == frames:
        return matrix
    x_old = np.linspace(0, 1, matrix.shape[1])
    x_new = np.linspace(0, 1, frames)
    return np.vstack([np.interp(x_new, x_old, row) for row in matrix])


def _normalize(matrix: np.ndarray) -> np.ndarray:
    return (matrix - np.mean(matrix)) / (np.std(matrix) + 1e-6)


def _resize_bins(matrix: np.ndarray, bins: int) -> np.ndarray:
    if matrix.shape[0] == bins:
        return matrix
    y_old = np.linspace(0, 1, matrix.shape[0])
    y_new = np.linspace(0, 1, bins)
    return np.vstack([np.interp(y_old, y_new, np.zeros_like(y_new)) for _ in range(1)]) if matrix.size == 0 else np.vstack(
        [np.interp(y_new, y_old, matrix[:, col]) for col in range(matrix.shape[1])]
    ).T


def _zcr_frames(y: np.ndarray, frame: int = 1024, hop: int = 256) -> np.ndarray:
    if y.size < frame:
        y = np.pad(y, (0, frame - y.size))
    count = 1 + (len(y) - frame) // hop
    values = []
    for index in range(max(count, 1)):
        segment = y[index * hop : index * hop + frame]
        values.append(np.mean(np.abs(np.diff(np.signbit(segment)))))
    return np.asarray(values)


def extract_multichannel_tensor(wav_path: str | Path, frames: int = 256, bins: int = 64) -> np.ndarray:
    y, sr = load_audio_fast(wav_path, TARGET_SAMPLE_RATE, mono=True)
    y = y / (np.max(np.abs(y)) + 1e-8)
    frequencies, _, stft = signal.stft(y, fs=sr, window="hann", nperseg=1024, noverlap=768)
    magnitude = np.abs(stft) + 1e-8
    power = magnitude**2
    log_power = np.log(power)
    band_energy = np.vstack([np.mean(split, axis=0) for split in np.array_split(log_power, bins, axis=0)])
    cepstra = dct(band_energy, axis=0, norm="ortho")
    delta = np.diff(cepstra, axis=1, prepend=cepstra[:, :1])
    delta2 = np.diff(delta, axis=1, prepend=delta[:, :1])
    flatness = np.exp(np.mean(np.log(magnitude), axis=0)) / (np.mean(magnitude, axis=0) + 1e-8)
    centroid = np.sum(frequencies[:, None] * power, axis=0) / (np.sum(power, axis=0) + 1e-8)
    zcr = _resize_time(_zcr_frames(y)[None, :], magnitude.shape[1])[0]
    contrast = np.percentile(magnitude, 90, axis=0) - np.percentile(magnitude, 10, axis=0)

    summary_maps = [
        np.tile(flatness, (bins, 1)),
        np.tile(centroid / (sr / 2), (bins, 1)),
        np.tile(contrast, (bins, 1)),
        np.tile(zcr, (bins, 1)),
    ]

    channels = []
    for matrix in (band_energy, cepstra, delta, delta2, *summary_maps):
        matrix = _resize_bins(matrix, bins)
        matrix = _resize_time(matrix, frames)
        channels.append(_normalize(matrix))

    return np.stack(channels[:8]).astype(np.float32)
