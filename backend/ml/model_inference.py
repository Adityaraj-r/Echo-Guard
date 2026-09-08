from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

from backend.config import (
    CALIBRATION_PATH,
    ENHANCED_MODEL_WEIGHTS_PATH,
    IS_PRODUCTION,
    MODEL_FAKE_CLASS_INDEX,
    MODEL_FUSION_CNN_WEIGHT,
    MODEL_HUMAN_CLASS_INDEX,
    MODEL_LEGACY_ONLY_CNN_WEIGHT,
    MODEL_WEIGHTS_PATH,
)
from backend.ml.calibration import calibrate_probability, load_temperature
from backend.ml.features import extract_forensic_features
from backend.ml.thresholds import categorize_prediction
from backend.ml.tensor_features import extract_multichannel_tensor
from backend.ml.model_definition import EchoGuardCNN, EchoGuardHybridNet


@lru_cache(maxsize=1)
def _load_legacy_model() -> EchoGuardCNN:
    model = EchoGuardCNN()
    if MODEL_WEIGHTS_PATH.exists():
        model.load_state_dict(torch.load(MODEL_WEIGHTS_PATH, map_location=torch.device("cpu")))
        print(f"Loaded legacy spectrogram weights from: {MODEL_WEIGHTS_PATH}")
    elif IS_PRODUCTION:
        raise RuntimeError(f"Model weights were not found at MODEL_WEIGHTS_PATH={MODEL_WEIGHTS_PATH}")
    else:
        print("No legacy weights found. Using initialized network. Set MODEL_WEIGHTS_PATH for production.")
    model.eval()
    return model


@lru_cache(maxsize=1)
def _load_hybrid_model() -> EchoGuardHybridNet | None:
    if not ENHANCED_MODEL_WEIGHTS_PATH.exists():
        return None
    model = EchoGuardHybridNet()
    payload = torch.load(ENHANCED_MODEL_WEIGHTS_PATH, map_location=torch.device("cpu"))
    state_dict = payload.get("model_state_dict", payload) if isinstance(payload, dict) else payload
    model.load_state_dict(state_dict)
    model.eval()
    print(f"Loaded enhanced hybrid weights from: {ENHANCED_MODEL_WEIGHTS_PATH}")
    return model


@lru_cache(maxsize=1)
def _image_transform():
    return transforms.Compose(
        [
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
        ]
    )


def _legacy_cnn_probability(image_path: str | Path) -> tuple[float, dict]:
    if MODEL_FAKE_CLASS_INDEX == MODEL_HUMAN_CLASS_INDEX:
        raise RuntimeError("MODEL_FAKE_CLASS_INDEX and MODEL_HUMAN_CLASS_INDEX must be different.")

    model = _load_legacy_model()
    image = Image.open(image_path).convert("RGB")
    input_tensor = _image_transform()(image).unsqueeze(0)

    with torch.no_grad():
        logits = model(input_tensor)
        probabilities = F.softmax(logits, dim=1)
        if max(MODEL_FAKE_CLASS_INDEX, MODEL_HUMAN_CLASS_INDEX) >= probabilities.shape[1]:
            raise RuntimeError(f"Configured class index exceeds output size: {probabilities.shape[1]}")
        fake_prob = probabilities[0][MODEL_FAKE_CLASS_INDEX].item()
        human_prob = probabilities[0][MODEL_HUMAN_CLASS_INDEX].item()

    return fake_prob, {
        "legacy_logits": logits.detach().cpu().tolist()[0],
        "legacy_fake_probability": round(fake_prob, 4),
        "legacy_human_probability": round(human_prob, 4),
    }


def _hybrid_probability(wav_path: str | Path) -> tuple[float | None, dict]:
    model = _load_hybrid_model()
    if model is None:
        return None, {"hybrid_model": "not_loaded"}

    tensor = torch.from_numpy(extract_multichannel_tensor(wav_path)).unsqueeze(0)
    with torch.no_grad():
        logits = model(tensor)
        probabilities = F.softmax(logits, dim=1)
        fake_prob = probabilities[0][MODEL_FAKE_CLASS_INDEX].item()
        human_prob = probabilities[0][MODEL_HUMAN_CLASS_INDEX].item()

    return fake_prob, {
        "hybrid_model": "loaded",
        "hybrid_fake_probability": round(fake_prob, 4),
        "hybrid_human_probability": round(human_prob, 4),
    }


def analyze_spectrogram(image_path: str) -> dict:
    fake_probability, debug = _legacy_cnn_probability(image_path)
    temperature = load_temperature(CALIBRATION_PATH)
    calibrated = calibrate_probability(fake_probability, temperature)
    category = categorize_prediction(calibrated)
    return _build_response(calibrated, category, {"temperature": temperature, **debug})


def analyze_audio_forensics(wav_path: str | Path, image_path: str | Path) -> dict:
    legacy_fake, legacy_debug = _legacy_cnn_probability(image_path)
    hybrid_fake, hybrid_debug = _hybrid_probability(wav_path)
    feature_report = extract_forensic_features(wav_path)
    artifact_score = feature_report["artifact_score"]
    temperature = load_temperature(CALIBRATION_PATH)
    calibrated_legacy = calibrate_probability(legacy_fake, temperature)

    if hybrid_fake is not None:
        calibrated_hybrid = calibrate_probability(hybrid_fake, temperature)
        neural_score = (calibrated_legacy + calibrated_hybrid) / 2
    else:
        calibrated_hybrid = None
        neural_score = calibrated_legacy

    cnn_weight = MODEL_FUSION_CNN_WEIGHT if hybrid_fake is not None else MODEL_LEGACY_ONLY_CNN_WEIGHT
    cnn_weight = float(np.clip(cnn_weight, 0.0, 1.0))
    artifact_score, guard_debug = _guard_live_voice_false_positive(
        artifact_score=artifact_score,
        neural_score=neural_score,
        feature_report=feature_report,
        hybrid_loaded=hybrid_fake is not None,
    )
    fused_fake = cnn_weight * neural_score + (1 - cnn_weight) * artifact_score

    disagreement = abs(neural_score - artifact_score)
    if disagreement > 0.42 and hybrid_fake is not None:
        fused_fake = (fused_fake + 0.5) / 2

    fused_fake = float(np.clip(fused_fake, 0.01, 0.99))
    category = categorize_prediction(fused_fake)
    if guard_debug["live_voice_guard_applied"] and category["prediction"] != "fake":
        feature_report = {
            **feature_report,
            "anomalies": [
                anomaly
                for anomaly in feature_report.get("anomalies", [])
                if anomaly
                not in {
                    "synthetic cepstral dynamics",
                    "synthetic acceleration dynamics",
                    "flat spectral texture",
                }
            ],
        }
    debug = {
        "temperature": temperature,
        "calibrated_legacy_fake_probability": round(calibrated_legacy, 4),
        "calibrated_hybrid_fake_probability": None if calibrated_hybrid is None else round(calibrated_hybrid, 4),
        "artifact_score": artifact_score,
        "fusion_cnn_weight": round(cnn_weight, 4),
        "model_artifact_disagreement": round(disagreement, 4),
        **guard_debug,
        **legacy_debug,
        **hybrid_debug,
    }
    return _build_response(fused_fake, category, debug, feature_report)


def _guard_live_voice_false_positive(
    artifact_score: float,
    neural_score: float,
    feature_report: dict,
    hybrid_loaded: bool,
) -> tuple[float, dict]:
    features = feature_report.get("features", {})
    expressive_low_band_voice = (
        neural_score < 0.58
        and artifact_score > 0.72
        and features.get("high_frequency_ratio", 1.0) < 0.03
        and features.get("zero_crossing_rate_std", 0.0) > 0.11
        and features.get("rms_std", 0.0) > 0.06
        and features.get("temporal_variance", 0.0) > 0.0003
        and features.get("phase_inconsistency", 9.0) < 1.58
    )
    should_guard = expressive_low_band_voice and not hybrid_loaded
    guarded_score = min(artifact_score, 0.30) if should_guard else artifact_score
    return guarded_score, {
        "live_voice_guard_applied": should_guard,
        "artifact_score_before_guard": round(float(artifact_score), 4),
    }


def _build_response(fake_probability: float, category: dict, debug: dict, feature_report: dict | None = None) -> dict:
    fake_probability = float(np.clip(fake_probability, 0.0, 1.0))
    human_probability = 1 - fake_probability
    return {
        "verdict": category["verdict"],
        "prediction": category["prediction"],
        "confidence": category["confidence"],
        "threat_score": round(fake_probability, 4),
        "fake_probability": round(fake_probability, 4),
        "human_probability": round(human_probability, 4),
        "risk_level": category["risk_level"],
        "ui_color": category["ui_color"],
        "is_uncertain": category["is_uncertain"],
        "explanation": category["explanation"],
        "forensic_features": feature_report.get("features", {}) if feature_report else {},
        "anomalies": feature_report.get("anomalies", []) if feature_report else [],
        "debug": debug,
        "class_mapping": {
            "fake": MODEL_FAKE_CLASS_INDEX,
            "human": MODEL_HUMAN_CLASS_INDEX,
        },
    }
