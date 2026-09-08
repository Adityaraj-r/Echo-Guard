import numpy as np
import librosa
from services.shared.config import Settings


class AudioProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings

    def to_mel_tensor(self, audio_path: str) -> list[list[list[float]]]:
        y, sr = librosa.load(
            audio_path,
            sr=self.settings.sample_rate,
            duration=self.settings.duration_seconds,
        )
        target_length = int(sr * self.settings.duration_seconds)
        if len(y) < target_length:
            y = np.pad(y, (0, target_length - len(y)), mode="constant")

        melspec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=self.settings.n_fft,
            hop_length=self.settings.hop_length,
            n_mels=self.settings.n_mels,
        )
        melspec_db = librosa.power_to_db(melspec, ref=np.max)
        normalized = (melspec_db + 80.0) / 80.0
        normalized = np.clip(normalized, 0.0, 1.0).astype("float32")

        # Model input shape is channel-first: [1, n_mels, time].
        return normalized[np.newaxis, :, :].tolist()
