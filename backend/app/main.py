"""Runnable, unavailable-by-design foundation for AFN-007 and AFN-008."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.predictor import ModelNotReadyError, Predictor, get_predictor
from app.schemas import CONTRACT_VERSION, ErrorResponse, HealthResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Resolve config at startup; importing this module never loads artifacts.
        app.state.settings = settings if settings is not None else Settings()
        app.state.predictor = None
        try:
            yield
        finally:
            # No model resources exist yet. A future owner must add actual cleanup.
            app.state.predictor = None
            app.state.settings = None

    app = FastAPI(title="Anti-fake-news local foundation", version=CONTRACT_VERSION,
                  lifespan=lifespan)

    @app.exception_handler(ModelNotReadyError)
    async def model_not_ready(request: Request, exc: ModelNotReadyError) -> JSONResponse:
        error = ErrorResponse(detail="Model is not ready", error_code="model_not_ready")
        return JSONResponse(status_code=503, content=error.model_dump(mode="json"))

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        # A configured path or injected object is not proof of model readiness.
        return HealthResponse(model_ready=False)

    @app.post(
        "/predict",
        status_code=503,
        response_model=ErrorResponse,
        summary="Disabled prediction skeleton (always 503)",
        description=(
            "Returns model_not_ready without reading the request body. "
            "Target multipart/auth/success contract: docs/api-contract.md v0.1.0. "
            "Transport validation, authentication and inference are deferred."
        ),
    )
    def predict(predictor: Annotated[Predictor, Depends(get_predictor)]) -> ErrorResponse:
        # Even a DI override cannot bypass missing auth/image validation.
        raise ModelNotReadyError

    return app


app = create_app()
