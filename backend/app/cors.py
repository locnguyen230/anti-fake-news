"""Exact local Extension origin policy, configured after application startup."""

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class LocalCORSMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        origin = scope["app"].state.settings.extension_origin
        # CORS surrounds auth so the allowed browser can read 401/400/413/503.
        # Preflight is unauthenticated; actual POST still passes token validation.
        cors = CORSMiddleware(
            self.app, allow_origins=[origin] if origin else [],
            allow_methods=["GET", "POST"], allow_headers=["X-Demo-Token", "Content-Type"],
            expose_headers=["X-AFN-Inference-Mode", "X-AFN-Model-State", "X-AFN-Decision-Threshold"],
            allow_credentials=False, max_age=600,
        )
        await cors(scope, receive, send)
