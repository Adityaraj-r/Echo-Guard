from pathlib import Path

import librosa
import librosa.display
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


LEGACY_SAMPLE_RATE = 22050
LEGACY_MEL_BINS = 128
LEGACY_N_FFT = 2048
LEGACY_HOP_LENGTH = 512
LEGACY_DURATION_SECONDS = 5.0


def generate_legacy_mel_spectrogram(
    audio_path: str | Path,
    output_image_path: str | Path,
    duration: float = LEGACY_DURATION_SECONDS,
) -> str | None:
    """Generate the historical mel image used by EchoGuard's legacy CNN.

    This is intentionally separate from NEW's linear-STFT visualization and
    model-image preprocessing. Callers should pass the original audio when
    this compatibility mode is explicitly selected.
    """
    try:
        y, sr = librosa.load(audio_path, sr=LEGACY_SAMPLE_RATE, mono=True, duration=duration)
        target_length = int(sr * duration)
        if len(y) < target_length:
            y = np.pad(y, (0, target_length - len(y)), mode="constant")

        mel_spectrogram = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=LEGACY_N_FFT,
            hop_length=LEGACY_HOP_LENGTH,
            n_mels=LEGACY_MEL_BINS,
        )
        mel_spectrogram_db = librosa.power_to_db(mel_spectrogram, ref=np.max)

        output_path = Path(output_image_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        plt.figure(figsize=(5, 5), dpi=100)
        try:
            plt.axis("off")
            plt.margins(0, 0)
            plt.gca().xaxis.set_major_locator(plt.NullLocator())
            plt.gca().yaxis.set_major_locator(plt.NullLocator())
            librosa.display.specshow(
                mel_spectrogram_db,
                sr=sr,
                hop_length=LEGACY_HOP_LENGTH,
                cmap="magma",
            )
            plt.savefig(output_path, bbox_inches="tight", pad_inches=0, transparent=True)
        finally:
            plt.close()

        return str(output_path)
    except Exception as exc:
        print(f"Legacy mel-spectrogram generation failed: {exc}")
        return None
