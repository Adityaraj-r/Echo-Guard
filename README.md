# EchoGuard

EchoGuard is a forensic audio analysis platform for detecting synthetic or deepfake voice clips. It combines a FastAPI backend, React/Vite dashboard, audio normalization, waveform and spectrogram visualization, and PyTorch-based model inference.

## Features

- React + Vite dashboard with upload, live microphone capture, waveform preview, result cards, and detection history.
- FastAPI backend with multi-format audio upload support.
- FFmpeg-based conversion to normalized mono WAV.
- Spectrogram and waveform generation for visual inspection.
- Legacy ResNet18 spectrogram inference plus forensic feature scoring.
- Optional enhanced hybrid model path for richer tensor-based inference.
- MongoDB-backed detection history when the database is available.
