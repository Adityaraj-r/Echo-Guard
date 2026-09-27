from backend.config import MODEL_FAKE_THRESHOLD, MODEL_HUMAN_THRESHOLD


def categorize_prediction(fake_probability: float) -> dict:
    fake_percent = round(fake_probability * 100, 2)
    human_percent = round((1 - fake_probability) * 100, 2)

    if fake_probability <= MODEL_HUMAN_THRESHOLD:
        return {
            "prediction": "human",
            "verdict": "Likely Human",
            "risk_level": "Low",
            "confidence": human_percent,
            "ui_color": "green",
            "is_uncertain": False,
            "explanation": "The calibrated fake probability is below the human threshold.",
        }

    if fake_probability >= MODEL_FAKE_THRESHOLD:
        return {
            "prediction": "fake",
            "verdict": "Likely AI Generated",
            "risk_level": "High",
            "confidence": fake_percent,
            "ui_color": "red",
            "is_uncertain": False,
            "explanation": "The calibrated fake probability is above the AI-generated threshold.",
        }

    return {
        "prediction": "uncertain",
        "verdict": "Uncertain",
        "risk_level": "Medium",
        "confidence": round(max(fake_percent, human_percent), 2),
        "ui_color": "amber",
        "is_uncertain": True,
            "explanation": (
                f"The calibrated fake probability is between the human threshold "
                f"({MODEL_HUMAN_THRESHOLD:.0%}) and fake threshold ({MODEL_FAKE_THRESHOLD:.0%}). "
                "Request more audio or corroborating evidence."
            ),
    }
