from pathlib import Path

import numpy as np
from scipy import signal
from scipy.fftpack import dct

from backend.config import TARGET_SAMPLE_RATE
from backend.preprocessing.audio_io import load_audio_fast


def _stats(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values)
    return (float(np.mean(values)), float(np.std(values))) if values.size else (0.0, 0.0)


def _smooth_step(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    x = float(np.clip((value - low) / (high - low), 0.0, 1.0))
    return x * x * (3 - 2 * x)


def _frame_signal(y: np.ndarray, frame: int = 1024, hop: int = 256) -> np.ndarray:
    if y.size < frame:
        y = np.pad(y, (0, frame - y.size))
    count = 1 + (len(y) - frame) // hop
    return np.stack([y[i * hop : i * hop + frame] for i in range(max(count, 1))])


def _band_energy(magnitude: np.ndarray, bands: int = 32) -> np.ndarray:
    splits = np.array_split(magnitude, bands, axis=0)
    return np.vstack([np.mean(split, axis=0) for split in splits])


def extract_forensic_features(wav_path: str | Path) -> dict:
    y, sr = load_audio_fast(wav_path, TARGET_SAMPLE_RATE, mono=True)
    if y.size == 0:
        return {"artifact_score": 0.5, "features": {}, "anomalies": []}

    peak = np.max(np.abs(y)) + 1e-8
    y = y / peak
    frames = _frame_signal(y)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    zcr = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1)

    frequencies, times, stft = signal.stft(y, fs=sr, window="hann", nperseg=1024, noverlap=768)
    magnitude = np.abs(stft) + 1e-8
    power = magnitude**2
    total_power = np.sum(power, axis=0) + 1e-8
    centroid = np.sum(frequencies[:, None] * power, axis=0) / total_power
    cumulative = np.cumsum(power, axis=0)
    rolloff_idx = np.argmax(cumulative >= 0.95 * total_power, axis=0)
    rolloff = frequencies[np.clip(rolloff_idx, 0, len(frequencies) - 1)]
    flatness = np.exp(np.mean(np.log(magnitude), axis=0)) / (np.mean(magnitude, axis=0) + 1e-8)

    band_energy = _band_energy(np.log(power + 1e-8), bands=32)
    cepstra = dct(band_energy, axis=0, norm="ortho")[:20]
    delta = np.diff(cepstra, axis=1)
    delta2 = np.diff(delta, axis=1)
    contrast = np.percentile(magnitude, 90, axis=0) - np.percentile(magnitude, 10, axis=0)
    phase = np.unwrap(np.angle(stft), axis=1)
    phase_inconsistency = float(np.mean(np.abs(np.diff(phase, axis=1)))) if phase.shape[1] > 1 else 0.0
    temporal_variance = float(np.var(np.diff(rms))) if rms.size > 1 else 0.0
    low_band = np.sum(power[frequencies < 4000])
    high_band = np.sum(power[frequencies >= 4000])
    high_frequency_ratio = float(high_band / (low_band + high_band + 1e-8))

    mfcc_delta_var = float(np.mean(np.var(delta, axis=1))) if delta.size else 0.0
    mfcc_accel_var = float(np.mean(np.var(delta2, axis=1))) if delta2.size else 0.0
    contrast_mean, contrast_std = _stats(contrast)
    zcr_mean, zcr_std = _stats(zcr)
    flatness_mean, flatness_std = _stats(flatness)
    rolloff_mean, rolloff_std = _stats(rolloff)
    centroid_mean, centroid_std = _stats(centroid)
    rms_mean, rms_std = _stats(rms)

    features = {
        "mfcc_delta_variance": mfcc_delta_var,
        "mfcc_acceleration_variance": mfcc_accel_var,
        "spectral_contrast_mean": contrast_mean,
        "spectral_contrast_std": contrast_std,
        "zero_crossing_rate_mean": zcr_mean,
        "zero_crossing_rate_std": zcr_std,
        "spectral_flatness_mean": flatness_mean,
        "spectral_flatness_std": flatness_std,
        "spectral_rolloff_mean": rolloff_mean,
        "spectral_rolloff_std": rolloff_std,
        "spectral_centroid_mean": centroid_mean,
        "spectral_centroid_std": centroid_std,
        "rms_mean": rms_mean,
        "rms_std": rms_std,
        "phase_inconsistency": phase_inconsistency,
        "temporal_variance": temporal_variance,
        "high_frequency_ratio": high_frequency_ratio,
    }

    dynamics_score = _smooth_step(mfcc_delta_var, 0.28, 0.72)
    acceleration_score = _smooth_step(mfcc_accel_var, 0.25, 0.78)
    flatness_score = _smooth_step(flatness_mean, 0.20, 0.36)
    phase_score = _smooth_step(phase_inconsistency, 1.62, 1.78)
    high_frequency_score = _smooth_step(high_frequency_ratio, 0.08, 0.34)
    low_variation_score = 1 - _smooth_step(rms_std, 0.018, 0.065)
    low_temporal_score = 1 - _smooth_step(temporal_variance, 0.00006, 0.00022)

    natural_voice_score = 0.0
    if high_frequency_ratio < 0.025 and rms_std > 0.045 and zcr_std > 0.04 and mfcc_delta_var < 0.28:
        natural_voice_score += 0.08
    if mfcc_delta_var < 0.24 and mfcc_accel_var > 0.08:
        natural_voice_score += 0.08

    artifact_score = (
        0.24
        + 0.34 * dynamics_score
        + 0.18 * acceleration_score
        + 0.11 * flatness_score
        + 0.08 * phase_score
        + 0.06 * high_frequency_score
        + 0.04 * low_variation_score
        + 0.04 * low_temporal_score
        - natural_voice_score
    )
    artifact_score = float(np.clip(artifact_score, 0.05, 0.95))

    anomaly_checks = [
        ("synthetic cepstral dynamics", dynamics_score > 0.62, 0.0),
        ("synthetic acceleration dynamics", acceleration_score > 0.62, 0.0),
        ("flat spectral texture", flatness_score > 0.55, 0.0),
        ("phase irregularity", phase_score > 0.55, 0.0),
        ("unusual high-frequency ratio", high_frequency_score > 0.55, 0.0),
        ("low amplitude variation", low_variation_score > 0.75, 0.0),
        ("low temporal variance", low_temporal_score > 0.75, 0.0),
    ]
    anomalies = []
    for label, active, _weight in anomaly_checks:
        if active:
            anomalies.append(label)

    return {
        "artifact_score": round(artifact_score, 4),
        "features": {key: round(float(value), 6) for key, value in features.items()},
        "anomalies": anomalies,
    }
