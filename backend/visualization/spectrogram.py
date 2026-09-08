from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from backend.preprocessing.audio_io import load_audio_fast


def create_forensic_spectrogram(audio_path: Path, output_path: Path, sample_rate: int) -> Path:
    y, sr = load_audio_fast(audio_path, sample_rate, mono=True)
    if y.size == 0:
        y = np.zeros(sample_rate, dtype=np.float32)

    frequencies, times, spectrum = signal.spectrogram(
        y,
        fs=sr,
        window="hann",
        nperseg=1024,
        noverlap=768,
        scaling="spectrum",
        mode="magnitude",
    )
    spectrum_db = 20 * np.log10(spectrum + 1e-8)

    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=140, facecolor="#101419")
    ax.set_facecolor("#101419")
    mesh = ax.pcolormesh(times, frequencies, spectrum_db, shading="auto", cmap="magma")
    ax.set_ylim(0, min(sr / 2, 11025))
    ax.set_title("Frequency forensic spectrogram", color="#eef2ff", pad=12)
    ax.set_xlabel("Time", color="#cbd5e1")
    ax.set_ylabel("Frequency", color="#cbd5e1")
    ax.tick_params(colors="#94a3b8")
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.ax.yaxis.set_tick_params(color="#94a3b8")
    plt.setp(cbar.ax.get_yticklabels(), color="#94a3b8")
    cbar.set_label("Magnitude (dB)", color="#cbd5e1")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return output_path
