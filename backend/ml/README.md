# EchoGuard ML Pipeline

## Why The Old Model Clustered Scores

The previous inference path used only a 128x128 spectrogram image and raw softmax. If the model was trained with limited data, class imbalance, mismatched class order, or visually similar spectrograms, both real and synthetic clips land in the same region of feature space. Raw softmax then gives confident but poorly calibrated probabilities.

## Before

1. Audio -> fixed 5s spectrogram image
2. ResNet18 image classifier
3. Raw softmax
4. Fake if fake probability is highest

## After

1. Audio -> normalized WAV
2. Multi-channel forensic tensor: mel, MFCC, delta MFCC, delta-delta, spectral contrast, chroma, ZCR, flatness
3. CNN + BiLSTM model for temporal artifacts
4. Temperature calibration
5. Handcrafted artifact score fusion
6. Threshold bands:
   - 0-35%: Likely Human
   - 35-65%: Uncertain
   - 65-100%: Likely AI Generated

## Recommended Datasets

- ASVspoof 2019 LA and ASVspoof 2021 DF
- WaveFake
- Fake-or-Real (FoR)
- In-the-wild deepfake speech datasets
- Your own microphone recordings from target devices

Keep speaker, language, codec, and recording device distributions balanced across real/fake splits.

## Training

Create a manifest:

```csv
path,label
C:\data\real_001.wav,human
C:\data\fake_001.wav,fake
```

Run:

```powershell
..\venv\Scripts\python.exe -m training.train_forensic_model --manifest data\manifest.csv --output-dir runs\echoguard_hybrid
```

Then set:

```env
ENHANCED_MODEL_WEIGHTS_PATH=runs\echoguard_hybrid\echoguard_hybrid_weights.pth
CALIBRATION_PATH=runs\echoguard_hybrid\calibration.json
```

## Debugging Real/Fake Separation

- Check confusion matrix, per-class precision/recall, ROC-AUC, and calibration NLL.
- Plot fake probability histograms for real vs fake. They should separate.
- Inspect uncertain cases and add more matching codec/device data.
- Keep test speakers disjoint from train speakers to avoid identity leakage.
- For CPU inference, keep clips <=30s, use `torch.no_grad()`, cache loaded models, and prefer the hybrid model over running multiple large models.
