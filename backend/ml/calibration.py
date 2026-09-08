import json
from pathlib import Path

import numpy as np

from backend.config import MODEL_TEMPERATURE


def load_temperature(path: Path) -> float:
    if not path.exists():
        return MODEL_TEMPERATURE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return max(float(payload.get("temperature", MODEL_TEMPERATURE)), 0.05)
    except Exception:
        return MODEL_TEMPERATURE


def softmax_with_temperature(logits, temperature: float) -> np.ndarray:
    values = np.asarray(logits, dtype=np.float64) / max(temperature, 0.05)
    values = values - np.max(values)
    exp = np.exp(values)
    return exp / np.sum(exp)


def calibrate_probability(probability: float, temperature: float) -> float:
    probability = float(np.clip(probability, 1e-6, 1 - 1e-6))
    logit = np.log(probability / (1 - probability))
    return float(1 / (1 + np.exp(-logit / max(temperature, 0.05))))
