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

## Project Structure

```text
backend/
  api/                 FastAPI routes
  app/                 database models and repository layer
  ml/                  calibration, thresholds, forensic features, tensors
  preprocessing/       validation, upload persistence, audio normalization
  services/            detection orchestration
  utils/               FFmpeg, filenames, startup helpers
  visualization/       waveform and spectrogram rendering
frontend/src/
  components/          dashboard UI components
  hooks/               microphone recording and detection hooks
  layouts/             app shell
  pages/               dashboard page
  services/            API client
  utils/               browser, WAV, formatting helpers
training/
  train_forensic_model.py
```

## Backend Setup

```powershell
cd "C:\Users\aadir\Desktop\eaco gaurd\echoguard"
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
..\.venv\Scripts\uvicorn.exe main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Frontend Setup

```powershell
cd "C:\Users\aadir\Desktop\eaco gaurd\echoguard\frontend"
npm install
npm run dev
```

Open:
####readme file 
```text
http://127.0.0.1:5173
```

## Important Environment Settings

```env
ENVIRONMENT=development
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=echoguard
UPLOAD_DIR=uploads
FFMPEG_PATH=ffmpeg
MODEL_WEIGHTS_PATH=echoguard_weights.pth
MODEL_FAKE_CLASS_INDEX=0
MODEL_HUMAN_CLASS_INDEX=1
MODEL_FAKE_THRESHOLD=0.65
MODEL_HUMAN_THRESHOLD=0.35
MODEL_LEGACY_ONLY_CNN_WEIGHT=0.2
MODEL_FUSION_CNN_WEIGHT=0.35
```

FFmpeg and ffprobe must be available on `PATH`, or `FFMPEG_PATH` / `FFPROBE_PATH` must point to them. Without FFmpeg, compressed uploads and browser recordings can fail conversion.

## Verification

```powershell
..\.venv\Scripts\python.exe -m compileall main.py backend training
..\.venv\Scripts\python.exe -c "import main; print(main.app.title)"
cd frontend
npm run build
```

## Notes

- Uploaded and generated runtime files are stored under `uploads/` and `temp_images/`.
- If MongoDB is unavailable, analysis can still return a result, but persisted history APIs return `503`.
- Browser microphone capture works on `localhost`, `127.0.0.1`, or HTTPS. Plain HTTP LAN URLs usually cannot access the microphone.
- Keep model weights, uploaded audio, generated images, logs, `node_modules`, `dist`, and virtualenvs out of git.
