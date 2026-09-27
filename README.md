<<<<<<< HEAD
# 🛡️ EchoGuard: Vishing Defense

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.11.0-EE4C2C)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136.0-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56.0-FF4B4B)

**EchoGuard** is a defense system against AI-generated voice phishing (Vishing) attacks. By converting audio signals into visual Mel-Spectrogram textures, EchoGuard utilizes a high-performance Convolutional Neural Network (CNN) to mathematically distinguish between authentic human voices and synthetic AI deepfakes.

## ✨ Key Features
- **Real-Time API Processing:** High-performance asynchronous API using FastAPI.
- **Audio-to-Image Transformation:** Uses `librosa` to map time-domain waveforms into frequency-domain Mel-Spectrograms (Magma colormap).
- **Deepfake Classification:** Modified PyTorch ResNet18 architecture tailored specifically for texture-based deepfake artifact detection.
- **Interactive UI Dashboard:** Built with Streamlit for a fast, intuitive, and user-friendly defense dashboard.

## 🛠️ Technology Stack
- **Frontend Dashboard:** Streamlit
- **Backend API:** FastAPI & Uvicorn
- **Audio Signal Processing:** Librosa, Matplotlib, Numpy
- **Artificial Intelligence Framework:** PyTorch & Torchvision

## 🧠 How it Works

1. **Ingestion & Standardization (`main.py`):** The system receives a `.wav` file and processes it via the REST API.
2. **Acoustic Frequency Mapping (`audio_processor.py`):** The audio is standardized to a `22050 Hz` sample rate and strictly zero-padded to 5 seconds. The Fast Fourier Transform (FFT) generates a high-contrast Mel-Spectrogram image representing the audio in decibels (dB), stripping out all axes for pure data pixels.
3. **Neural Network Inference (`model_definition.py` & `model_inference.py`):** The image is normalized and passed into a modified **ResNet18 CNN**. The model is trained to spot mathematical visual anomalies and acoustic artifacts exclusively left by AI voice synthesizers (e.g., ElevenLabs).
4. **Final Verdict:** The network issues a confidence probability, displayed on the Streamlit dashboard alongside the visual spectrogram data.

## 🚀 Installation & Execution

### Prerequisites
Make sure you have Python 3.8+ installed. It is recommended to use a virtual environment.

### 1. Setup the Environment
Clone the repository and install the dependencies:
```bash
python -m venv venv

# On Windows
.\venv\Scripts\activate

# On Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Start the Backend API
You will need to open **two** terminal windows. In the first terminal (ensure the `venv` is active):
```bash
uvicorn main:app --reload
```
*The FastAPI server will start locally on port 8000.*

### 3. Start the Frontend Dashboard
In the second terminal (ensure the `venv` is active):
```bash
streamlit run app.py
```
*Your browser will open automatically to the EchoGuard UI at `http://localhost:8501`.*

## 📂 Project Structure
```
echoguard-vishing/
│
├── app.py                     # Streamlit User Interface
├── main.py                    # FastAPI Backend Server
├── audio_processor.py         # Librosa audio-to-spectrogram pipeline
├── model_definition.py        # PyTorch ResNet18 CNN Architecture
├── model_inference.py         # AI Model inference and threshold logic
├── augment_data.py            # Data augmentation utilities
├── echoguard_weights.pth      # Trained neural network weights
└── requirements.txt           # Python dependencies
```

## ⚠️ Disclaimer
This system is designed as an educational tool for cybersecurity defense and acoustic research. Please do not use it for production-level automated security blocking without further adversarial training.
=======
# EchoGuard

EchoGuard is a forensic AI audio analysis platform for detecting synthetic or deepfake voice clips. The upgraded app includes a responsive React cybersecurity dashboard, FastAPI backend, live microphone capture, multi-format audio conversion, waveform visualization, spectrogram generation, metadata extraction, and model inference through the existing PyTorch pipeline.

## Features

- Responsive React + Vite dashboard with TailwindCSS, glass panels, dark mode, and Framer Motion animations
- Drag-and-drop upload for `.wav`, `.aac`, `.m4a`, `.flac`, `.mp3`, `.aiff`, `.ogg`, `.wma`, `.dsf`, and `.dff`
- Live microphone recording with `MediaRecorder` and browser waveform preview
- Centralized backend `process_audio()` pipeline using FFmpeg + pydub, librosa, matplotlib, and PyTorch
- Normalized WAV conversion at 22,050 Hz, mono, PCM 16-bit
- Waveform data, dark forensic spectrograms, confidence meters, risk labels, and audio metadata
- Session detection history in the UI

## Project Structure

```text
backend/
  api/                 FastAPI routes
  models/              Model-facing package boundary
  preprocessing/       Validation, conversion, normalization, waveform, metadata
  services/            Detection orchestration
  uploads/             Runtime upload, processed WAV, and spectrogram output
  utils/               Filename and asset helpers
  visualization/       Spectrogram rendering
frontend/src/
  components/          Reusable dashboard UI
  hooks/               Microphone recording hook
  layouts/             Responsive app shell
  pages/               Dashboard page
  services/            API client
  utils/               Formatting helpers
```

## Backend Setup

```powershell
cd "c:\Users\aadir\Desktop\eaco gaurd\echoguard"
..\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Default local settings:

```env
ENVIRONMENT=development
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=echoguard
UPLOAD_DIR=uploads
FFMPEG_PATH=ffmpeg
MODEL_WEIGHTS_PATH=echoguard_weights.pth
```

Start MongoDB locally, or replace `MONGODB_URL` with your MongoDB Atlas connection string.

Start the API:

```powershell
..\venv\Scripts\uvicorn.exe main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Frontend Setup

```powershell
cd "c:\Users\aadir\Desktop\eaco gaurd\echoguard\frontend"
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Microphone Testing

Browser microphone APIs only work in a secure context:

- Works locally: `http://localhost:5173` or `http://127.0.0.1:5173`
- Works in production: HTTPS deployment
- Does not work: plain HTTP from another device, such as `http://192.168.x.x:5173`

Chrome, Edge, Firefox, and most Android browsers require you to allow microphone permission when prompted. If permission was denied earlier, open the browser site settings and reset microphone access.

For desktop testing, do not open the LAN IP. Use:

```text
http://127.0.0.1:5173
```

For mobile or another device on your LAN, run Vite with HTTPS:

```powershell
npm run dev:https
```

Open the HTTPS LAN URL shown by Vite, for example:

```text
https://192.168.0.116:5173
```

The browser will show a self-signed certificate warning during local development. Accept it only for your own dev machine.

If you have your own trusted certificate, you can provide it:

```powershell
$env:VITE_HTTPS="true"
$env:VITE_HTTPS_KEY="C:\path\to\localhost-key.pem"
$env:VITE_HTTPS_CERT="C:\path\to\localhost-cert.pem"
npm run dev -- --host 0.0.0.0
```

The Vite dev server proxies `/api` and `/assets` to FastAPI, so mobile browsers can call the backend through the same HTTPS origin.

Optional API override:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Production Checklist

Before pushing to a new public or private repo:

- Do not commit `.env`, uploaded audio, generated images, logs, `node_modules`, `dist`, virtualenvs, or model weight files. These are covered by `.gitignore`.
- Keep `echoguard_weights.pth` outside git. In production, provide it through secure storage or a mounted volume and set `MODEL_WEIGHTS_PATH`.
- Set `ENVIRONMENT=production` to disable interactive API docs and reduce internal error leakage.
- Set `CORS_ORIGINS` to the exact frontend origin, for example `https://app.example.com`.
- Set `ALLOWED_HOSTS` to the API hostnames, for example `api.example.com,localhost`.
- Set `MONGODB_URL` from your secret manager, not in source control.
- Install FFmpeg on the host/container and set `FFMPEG_PATH` if it is not on `PATH`.
- Keep `MAX_UPLOAD_SIZE_MB` aligned with your reverse proxy limit.

Minimal production API environment:

```env
ENVIRONMENT=production
MONGODB_URL=mongodb+srv://USER:PASSWORD@cluster.example.mongodb.net
DATABASE_NAME=echoguard
CORS_ORIGINS=https://app.example.com
ALLOWED_HOSTS=api.example.com
UPLOAD_DIR=/data/uploads
TEMP_AUDIO_DIR=/data/temp_audio
TEMP_IMAGE_DIR=/data/temp_images
FFMPEG_PATH=/usr/bin
MODEL_WEIGHTS_PATH=/models/echoguard_weights.pth
MAX_UPLOAD_SIZE_MB=25
```

Build checks:

```powershell
..\venv\Scripts\python.exe -m compileall main.py backend model_inference.py
cd frontend
npm run build
```

Docker API image:

```powershell
docker build -t echoguard-api .
docker run --env-file .env -p 8000:8000 -v ${PWD}\uploads:/data/uploads -v ${PWD}\echoguard_weights.pth:/models/echoguard_weights.pth:ro echoguard-api
```

Docker Compose for the API, frontend, and MongoDB:

```powershell
docker compose up --build
```

Compose expects `echoguard_weights.pth` to exist in the project root and mounts it read-only into the API container. Open the app at:

```text
http://localhost:8080
```

## FFmpeg Setup on Windows

Multi-format decoding depends on FFmpeg and ffprobe being available on `PATH`.

Recommended install with winget:

```powershell
winget install Gyan.FFmpeg
```

Then restart the terminal and verify:

```powershell
ffmpeg -version
ffprobe -version
```

If winget is unavailable, download a Windows FFmpeg build, extract it, and add its `bin` folder to your system `PATH`.

## Verification

Backend syntax/import checks:

```powershell
..\venv\Scripts\python.exe -m compileall main.py backend model_inference.py
..\venv\Scripts\python.exe -c "import main; print(main.app.title)"
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Notes

- The existing CNN spectrogram inference path remains in use through `audio_processor.py` and `model_inference.py`.
- Without FFmpeg on `PATH`, pydub may still handle simple WAV files, but compressed formats and live browser recordings can fail.
- Generated runtime files are stored under `uploads/` and `temp_images/`.
- Detection history is stored in MongoDB through Motor + Beanie. If MongoDB is not reachable, analysis can still return a result, but persisted history APIs return `503`.
- Uploaded and generated artifacts are stored in `uploads/audio/`, `uploads/waveforms/`, and `uploads/spectrograms/`.
>>>>>>> 2d6d0ad (update the whole project)
