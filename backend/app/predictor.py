"""Predictor protocol, multimodal provider, and dependency for request handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from pathlib import Path

from fastapi import Request
from pydantic import Field

from app.errors import InputError
from app.preprocessing import EMBEDDING_DTYPE_NAME, PreprocessingError, load_image_rgb
from app.schemas import PredictFormFields, PredictionResult

if TYPE_CHECKING:
    from app.clip_encoder import ImageEncoder
    from app.model_bundle import ModelBundle


class PredictorInput(PredictFormFields):
    """Proposed boundary: validated encoded JPEG/PNG bytes; ML review pending."""

    image_bytes: bytes = Field(strict=True, min_length=1, repr=False)


class ModelNotReadyError(RuntimeError):
    """Model is absent, unavailable or incompatible; never expose exception text."""


class Predictor(Protocol):
    def predict(self, inputs: PredictorInput) -> PredictionResult:
        """Synchronous CPU inference after Backend validation; may raise ModelNotReadyError."""
        ...


class BundlePredictor:
    def __init__(self, bundle: ModelBundle, encoder: ImageEncoder) -> None:
        self._bundle = bundle
        self._encoder = encoder

    def predict(self, inputs: PredictorInput) -> PredictionResult:
        if self._encoder is None or self._bundle is None:
            raise ModelNotReadyError
        try:
            with load_image_rgb(inputs.image_bytes) as image:
                embedding = self._encoder.encode([image])
            if embedding.dtype.name != EMBEDDING_DTYPE_NAME:
                raise ValueError("encoder returned an unexpected dtype")
            result = self._bundle.predict(inputs.title, inputs.text, embedding)
        except PreprocessingError:
            raise InputError(inputs.request_id) from None
        return PredictionResult.model_validate(result, from_attributes=True)

    def close(self) -> None:
        encoder, self._encoder = self._encoder, None
        self._bundle = None
        close = getattr(encoder, "close", None)
        if callable(close):
            close()


def load_for_parity(bundle_dir: Path) -> BundlePredictor:
    """AFN-036 factory hook; same loader/warm-up as HTTP, no .env or training."""
    from app.config import Settings
    from app.model_loader import load_predictor

    return load_predictor(Settings(_env_file=None, environment="test", predictor_mode="real",
                                   model_artifact_path=bundle_dir))


def get_predictor(request: Request) -> Predictor:
    """Return the lifecycle-installed adapter or an explicit dependency override."""
    predictor: Predictor | None = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise ModelNotReadyError
    return predictor
