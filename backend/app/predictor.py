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
        self._bundle: ModelBundle | None = bundle
        self._encoder: ImageEncoder | None = encoder

    def close(self) -> None:
        encoder, self._encoder = self._encoder, None
        self._bundle = None
        close = getattr(encoder, "close", None)
        if callable(close):
            close()

    def predict(self, inputs: PredictorInput) -> PredictionResult:
        bundle, encoder = self._bundle, self._encoder
        if bundle is None or encoder is None:
            raise ModelNotReadyError
        try:
            with load_image_rgb(inputs.image_bytes) as image:
                embedding = encoder.encode([image])
            if embedding.dtype.name != EMBEDDING_DTYPE_NAME:
                raise ValueError("encoder returned an unexpected dtype")
            result = bundle.predict(inputs.title, inputs.text, embedding)
        except PreprocessingError:
            raise InputError(inputs.request_id) from None
        return PredictionResult.model_validate(result, from_attributes=True)


def load_for_parity(bundle_dir: Path | str) -> BundlePredictor:
    """Offline CLI factory using the serving loader, including checks and warm-up.

    Explicit test environment permits synthetic bundles. Neither .env nor AFN_*
    deployment settings select another provider or bypass bundle validation.
    The caller owns close(); this factory never trains or alters an artifact.
    """
    from app.config import Settings
    from app.model_loader import load_predictor

    return load_predictor(Settings(
        _env_file=None, _env_prefix="AFN_PARITY_",
        environment="test", predictor_mode="real", model_artifact_path=Path(bundle_dir),
        model_metadata_sha256=None, allow_candidate_model=False,
    ))


def get_predictor(request: Request) -> Predictor:
    """Return the lifecycle-installed adapter or an explicit dependency override."""
    predictor: Predictor | None = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise ModelNotReadyError
    return predictor
