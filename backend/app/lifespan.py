"""Keep ASGI lifecycle failures out of server logs without hiding failure state."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SanitizedLifespanMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "lifespan":
            await self.app(scope, receive, send)
            return

        async def sanitized_send(message: Message) -> None:
            if message["type"] in ("lifespan.startup.failed", "lifespan.shutdown.failed"):
                phase = "startup" if message["type"] == "lifespan.startup.failed" else "shutdown"
                message = {"type": message["type"], "message": f"Backend {phase} failed; check local configuration and model assets."}
            await send(message)

        # Starlette sends *.failed before reraising; Uvicorn then exits without
        # logging the exception again. Preserve this behavior and exit status.
        await self.app(scope, receive, sanitized_send)
