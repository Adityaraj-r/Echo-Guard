class ModelNotReadyError(RuntimeError):
    """Raised when the trained model cannot safely serve inference."""


_model_readiness = {"state": "not_checked", "ready": False}


def get_model_readiness() -> dict:
    return dict(_model_readiness)


def set_model_readiness(state: str, ready: bool) -> None:
    _model_readiness.update(state=state, ready=ready)
