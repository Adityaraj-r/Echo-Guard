import torch
import torch.nn as nn
import torchvision.models as models

class EchoGuardCNN(nn.Module):
    def __init__(self):
        super(EchoGuardCNN, self).__init__()
        # Load the powerful ResNet18 architecture
        self.resnet = models.resnet18(weights=None) 
        
        # Modify the final output layer from 1000 classes down to 2 (Real vs Fake)
        num_ftrs = self.resnet.fc.in_features
        self.resnet.fc = nn.Linear(num_ftrs, 2)

    def forward(self, x):
        return self.resnet(x)


class EchoGuardHybridNet(nn.Module):
    """
    Production training architecture for richer audio tensors.

    Expected input shape: [batch, channels, n_features, time]
    Channels can include mel, MFCC, delta MFCC, delta-delta, contrast, chroma,
    ZCR/flatness/centroid/rolloff summary maps.
    """

    def __init__(self, in_channels: int = 8, hidden_size: int = 128, num_classes: int = 2, dropout: float = 0.35):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.GELU(),
            nn.MaxPool2d((2, 2)),
            nn.Dropout2d(dropout * 0.5),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.GELU(),
            nn.MaxPool2d((2, 2)),
            nn.Dropout2d(dropout * 0.5),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.GELU(),
            nn.MaxPool2d((2, 1)),
        )
        self.feature_pool = nn.AdaptiveAvgPool2d((16, None))
        self.bilstm = nn.LSTM(
            input_size=128 * 16,
            hidden_size=hidden_size,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout,
        )
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_size * 2),
            nn.Dropout(dropout),
            nn.Linear(hidden_size * 2, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        x = self.cnn(x)
        x = self.feature_pool(x)
        x = x.permute(0, 3, 1, 2).flatten(2)
        sequence, _ = self.bilstm(x)
        pooled = sequence.mean(dim=1)
        return self.classifier(pooled)
