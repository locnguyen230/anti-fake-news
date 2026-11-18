"""DI seam only. No mock predictions, artifact loader, or readiness state machine."""

from typing import Protocol

from fastapi import Request
from pydantic import Field

from app.schemas import PredictFormFields, PredictionResult


class PredictorInput(PredictFormFields):
    """Proposed boundary: validated encoded JPEG/PNG bytes; ML review pending."""

    image_bytes: bytes = Field(strict=True, min_length=1, repr=False)


class ModelNotReadyError(RuntimeError):
    """Model is absent, unavailable or incompatible; never expose exception text."""


class Predictor(Protocol):
    def predict(self, inputs: PredictorInput) -> PredictionResult:
        """Synchronous CPU inference after Backend validation; may raise ModelNotReadyError."""
        ...


def get_predictor(request: Request) -> Predictor:
    """Future lifecycle integration can install a Predictor in app.state.predictor."""
    predictor: Predictor | None = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise ModelNotReadyError
    return predictor
