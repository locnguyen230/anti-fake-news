"""Provider state and failure boundary for real and explicit mock inference."""

from collections.abc import Callable
from enum import Enum
from typing import Literal

from fastapi import Request

from app.config import Settings
from app.errors import InputError
from app.predictor import ModelNotReadyError, Predictor, PredictorInput
from app.schemas import PredictionResult


class ModelState(str, Enum):
    NOT_LOADED = "not_loaded"
    READY = "ready"
    ERROR = "error"


class InferenceAdapter:
    def __init__(self, mode: Literal["real", "mock"] = "real") -> None:
        self._mode = mode
        self._state = ModelState.NOT_LOADED
        self._predictor: Predictor | None = None

    @property
    def mode(self) -> Literal["real", "mock"]:
        return self._mode

    @property
    def state(self) -> ModelState:
        return self._state

    @property
    def ready(self) -> bool:
        return self._state is ModelState.READY and self._predictor is not None

    def initialize(self, factory: Callable[[], Predictor]) -> None:
        """The lifecycle owner must supply a compatible, ready-to-use provider.

        Real initialization validates and warms up before returning its provider.
        Initialization failures are retained as ERROR.
        """
        self.close()
        try:
            predictor = factory()
            if not callable(getattr(predictor, "predict", None)):
                raise TypeError("Provider must implement predict")
            self._predictor = predictor
            self._state = ModelState.READY
        except Exception:
            self.mark_error()

    def mark_error(self) -> None:
        # Keep no exception strings, paths, credentials or article data in state.
        self._predictor = None
        self._state = ModelState.ERROR

    def close(self) -> None:
        self._predictor = None
        self._state = ModelState.NOT_LOADED

    def predict(self, inputs: PredictorInput) -> PredictionResult:
        predictor = self._predictor
        if not self.ready or predictor is None:
            raise ModelNotReadyError
        try:
            return PredictionResult.model_validate(predictor.predict(inputs))
        except InputError:
            raise
        except Exception:
            self.mark_error()
            raise ModelNotReadyError from None


def create_adapter(settings: Settings) -> InferenceAdapter:
    adapter = InferenceAdapter(mode=settings.predictor_mode)
    if settings.predictor_mode == "mock":
        # Defense in depth: never opt into mock based on artifact availability.
        if settings.environment not in ("dev", "test"):
            raise ValueError("Mock is restricted to dev/test")
        from app.dev.mock_predictor import MockPredictor

        adapter.initialize(MockPredictor)
    elif (
        settings.environment == "production"
        or "model_artifact_path" in settings.model_fields_set
        or settings.model_artifact_path.exists()
    ):
        def initialize_real() -> Predictor:
            from app.model_loader import load_predictor

            return load_predictor(settings)

        adapter.initialize(initialize_real)
    return adapter


def get_inference_adapter(request: Request) -> InferenceAdapter:
    return request.app.state.inference_adapter
