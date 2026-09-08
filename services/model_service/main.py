from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from backend.ml.model_definition import EchoGuardCNN
from services.shared.config import get_settings
from services.shared.logging import configure_logging, get_logger
from services.shared.schemas import BatchPredictionRequest, BatchPredictionResponse, Prediction

settings = get_settings()
configure_logging("model-service")
logger = get_logger(__name__)
app = FastAPI(title="EchoGuard Model Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)


class InferenceEngine:
    def __init__(self) -> None:
        self.device = torch.device("cuda" if settings.use_gpu and torch.cuda.is_available() else "cpu")
        self.onnx_session: ort.InferenceSession | None = None
        if Path(settings.model_path).exists():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if settings.use_gpu else ["CPUExecutionProvider"]
            available = ort.get_available_providers()
            providers = [provider for provider in providers if provider in available]
            self.onnx_session = ort.InferenceSession(settings.model_path, providers=providers)
            self.model_version = "resnet18-onnx"
            self.model = None
            return

        self.model = EchoGuardCNN().to(self.device)
        try:
            state = torch.load(settings.torch_weights_path, map_location=self.device)
            self.model.load_state_dict(state)
            self.model_version = "resnet18-pytorch"
        except FileNotFoundError:
            self.model_version = "resnet18-untrained"
            logger.warning("weights_not_found", path=settings.torch_weights_path)
        self.model.eval()

    def predict_batch(self, items: BatchPredictionRequest) -> dict[str, Prediction]:
        tensors = []
        job_ids = []
        for item in items.items:
            arr = np.array(item.spectrogram, dtype=np.float32)
            if arr.shape[0] == 1:
                arr = np.repeat(arr, 3, axis=0)
            tensors.append(torch.from_numpy(arr))
            job_ids.append(item.job_id)

        batch = torch.stack(tensors)
        batch = F.interpolate(batch, size=(128, 128), mode="bilinear", align_corners=False)
        batch = ((batch - 0.5) / 0.5).numpy().astype(np.float32)

        if self.onnx_session:
            logits = self.onnx_session.run(["logits"], {"spectrogram": batch})[0]
            probs = self._softmax(logits)
        else:
            assert self.model is not None
            torch_batch = torch.from_numpy(batch).to(self.device)
            with torch.no_grad():
                probs = F.softmax(self.model(torch_batch), dim=1).detach().cpu().numpy()

        predictions = {}
        for job_id, row in zip(job_ids, probs):
            fake_prob = float(row[0])
            human_prob = float(row[1])
            verdict = "Fake" if fake_prob > human_prob else "Human"
            confidence = fake_prob if verdict == "Fake" else human_prob
            if fake_prob >= 0.75:
                risk = "High"
            elif fake_prob >= 0.45:
                risk = "Medium"
            else:
                risk = "Low"

            print("Raw model output:", row.tolist())
            print("Fake probability:", fake_prob)
            print("Human probability:", human_prob)
            print("Final verdict:", verdict)

            predictions[job_id] = Prediction(
                verdict=verdict,
                confidence=round(confidence * 100, 2),
                fake_probability=round(fake_prob, 4),
                human_probability=round(human_prob, 4),
                risk_level=risk,
                synthetic_probability=round(fake_prob, 4),
                authentic_probability=round(human_prob, 4),
                model_version=self.model_version,
            )
        return predictions

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exps = np.exp(shifted)
        return exps / np.sum(exps, axis=1, keepdims=True)


engine: InferenceEngine | None = None


@app.on_event("startup")
async def startup() -> None:
    global engine
    engine = InferenceEngine()
    logger.info("model_loaded", device=str(engine.device), model_version=engine.model_version)


@app.post("/v1/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    assert engine is not None
    return BatchPredictionResponse(predictions=engine.predict_batch(request))
