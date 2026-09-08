import torch
from model_definition import EchoGuardCNN


def export_onnx(weights_path: str, output_path: str) -> None:
    model = EchoGuardCNN()
    model.load_state_dict(torch.load(weights_path, map_location="cpu"))
    model.eval()
    dummy = torch.randn(1, 3, 128, 128)
    torch.onnx.export(
        model,
        dummy,
        output_path,
        input_names=["spectrogram"],
        output_names=["logits"],
        dynamic_axes={"spectrogram": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )


if __name__ == "__main__":
    export_onnx("/models/echoguard_weights.pth", "/models/echoguard.onnx")
