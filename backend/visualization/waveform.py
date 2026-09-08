from pathlib import Path

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.preprocessing.audio_io import load_audio_fast


def create_waveform_image(audio_path: Path, output_path: Path, sample_rate: int) -> Path:
    y, sr = load_audio_fast(audio_path, sample_rate, mono=True)
    times = np.linspace(0, len(y) / sr if sr else 0, num=len(y))

    fig, ax = plt.subplots(figsize=(10, 2.6), dpi=140, facecolor="#101419")
    ax.set_facecolor("#101419")
    ax.plot(times, y, color="#67e8f9", linewidth=0.8)
    ax.fill_between(times, y, 0, color="#14b8a6", alpha=0.28)
    ax.set_title("Waveform envelope", color="#eef2ff", pad=10)
    ax.set_xlabel("Time", color="#cbd5e1")
    ax.set_ylabel("Amplitude", color="#cbd5e1")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return output_path
