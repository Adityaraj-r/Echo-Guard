import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

try:
    from torch.utils.tensorboard import SummaryWriter
except Exception:  # pragma: no cover
    SummaryWriter = None

from backend.ml.calibration import softmax_with_temperature
from backend.ml.tensor_features import extract_multichannel_tensor
from backend.config import MODEL_FAKE_CLASS_INDEX, MODEL_HUMAN_CLASS_INDEX
from backend.ml.model_definition import EchoGuardHybridNet


CLASS_NAMES = [""] * 2
CLASS_NAMES[MODEL_FAKE_CLASS_INDEX] = "fake"
CLASS_NAMES[MODEL_HUMAN_CLASS_INDEX] = "human"


class AudioCsvDataset(Dataset):
    def __init__(self, rows, augment=False):
        self.rows = rows
        self.augment = augment

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        path, label = self.rows[index]
        tensor = extract_multichannel_tensor(path)
        if self.augment:
            tensor = self._augment(tensor)
        return torch.from_numpy(tensor), torch.tensor(label, dtype=torch.long)

    def _augment(self, tensor):
        if np.random.rand() < 0.35:
            tensor = tensor + np.random.normal(0, 0.025, size=tensor.shape).astype(np.float32)
        if np.random.rand() < 0.25:
            shift = np.random.randint(-12, 12)
            tensor = np.roll(tensor, shift=shift, axis=-1)
        if np.random.rand() < 0.25:
            width = np.random.randint(8, 28)
            start = np.random.randint(0, max(1, tensor.shape[-1] - width))
            tensor[..., start : start + width] *= 0.15
        return tensor.astype(np.float32)


def load_manifest(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        audio_path, label = line.split(",")[:2]
        label_value = MODEL_FAKE_CLASS_INDEX if label.strip().lower() in {"fake", "synthetic", "ai", "1"} else MODEL_HUMAN_CLASS_INDEX
        rows.append((audio_path.strip(), label_value))
    return rows


def fit_temperature(logits, labels):
    temperatures = np.linspace(0.5, 6.0, 56)
    best_temp, best_nll = 1.0, float("inf")
    labels = np.asarray(labels)
    for temp in temperatures:
        probs = np.asarray([softmax_with_temperature(logit, temp) for logit in logits])
        nll = -np.mean(np.log(probs[np.arange(len(labels)), labels] + 1e-8))
        if nll < best_nll:
            best_temp, best_nll = float(temp), float(nll)
    return best_temp, best_nll




    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_manifest(Path(args.manifest))
    train_rows, val_rows = train_test_split(rows, test_size=0.2, stratify=[label for _, label in rows], random_state=42)

    class_counts = np.bincount([label for _, label in train_rows], minlength=2)
    weights = [1.0 / max(class_counts[label], 1) for _, label in train_rows]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

    train_loader = DataLoader(AudioCsvDataset(train_rows, augment=True), batch_size=args.batch_size, sampler=sampler, num_workers=0)
    val_loader = DataLoader(AudioCsvDataset(val_rows), batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = EchoGuardHybridNet().to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    writer = SummaryWriter(str(output_dir / "tensorboard")) if SummaryWriter else None

    best_auc = -1.0
    patience, bad_epochs = 6, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        losses = []
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            optimizer.step()
            losses.append(loss.item())
        scheduler.step()

        logits, labels, preds, auc = evaluate(model, val_loader, device)
        report = classification_report(labels, preds, labels=[0, 1], target_names=CLASS_NAMES, output_dict=True, zero_division=0)
        val_loss = float(np.mean([-np.log(softmax_with_temperature(logit, 1.0)[label] + 1e-8) for logit, label in zip(logits, labels)]))

        if writer:
            writer.add_scalar("loss/train", float(np.mean(losses)), epoch)
            writer.add_scalar("loss/val", val_loss, epoch)
            writer.add_scalar("auc/val", auc, epoch)
            writer.add_scalar("f1/fake", report["fake"]["f1-score"], epoch)

        if auc > best_auc:
            best_auc = auc
            bad_epochs = 0
            torch.save({"model_state_dict": model.state_dict(), "auc": auc, "epoch": epoch}, output_dir / "echoguard_hybrid_weights.pth")
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    logits, labels, preds, auc = evaluate(model, val_loader, device)
    temperature, nll = fit_temperature(logits, labels)
    (output_dir / "calibration.json").write_text(json.dumps({"temperature": temperature, "nll": nll}, indent=2), encoding="utf-8")

    cm = confusion_matrix(labels, preds)
    ConfusionMatrixDisplay(cm, display_labels=CLASS_NAMES).plot(cmap="Blues")
    plt.title(f"EchoGuard validation confusion matrix AUC={auc:.3f}")
    plt.tight_layout()
    plt.savefig(output_dir / "confusion_matrix.png", dpi=160)
    plt.close()

    report = classification_report(labels, preds, labels=[0, 1], target_names=CLASS_NAMES, output_dict=True, zero_division=0)
    (output_dir / "metrics.json").write_text(json.dumps({"auc": auc, "report": report}, indent=2), encoding="utf-8")
    if writer:
        writer.close()


if __name__ == "__main__":
    main()
