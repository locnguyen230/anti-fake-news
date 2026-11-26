"""AFN-053: fail closed without leaking lifecycle exception text to Uvicorn."""

import asyncio
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.lifespan import SanitizedLifespanMiddleware


@pytest.mark.parametrize("phase", ["startup", "shutdown"])
def test_failed_lifespan_message_is_sanitized_without_swallowing_error(phase):
    sent = []

    async def failing_app(scope, receive, send):
        await send({"type": f"lifespan.{phase}.failed", "message": "Traceback secret C:/private/model"})
        raise RuntimeError("private exception")

    async def send(message):
        sent.append(message)

    with pytest.raises(RuntimeError, match="private exception"):
        asyncio.run(SanitizedLifespanMiddleware(failing_app)({"type": "lifespan"}, None, send))
    assert sent == [{"type": f"lifespan.{phase}.failed",
                     "message": f"Backend {phase} failed; check local configuration and model assets."}]


def test_real_launcher_missing_production_model_exits_without_traceback(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    environment = {k: v for k, v in os.environ.items() if not k.upper().startswith("AFN_")}
    environment.update(AFN_ENVIRONMENT="production", AFN_PREDICTOR_MODE="real",
                       AFN_DEMO_TOKEN="logging-test-secret", AFN_MODEL_METADATA_SHA256="0" * 64,
                       AFN_MODEL_ARTIFACT_PATH=str(tmp_path / "private-missing-model"),
                       AFN_ALLOW_CANDIDATE_MODEL="false", HF_HUB_OFFLINE="1")
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    result = subprocess.run([sys.executable, "-m", "app"], cwd=backend, env=environment,
                            capture_output=True, text=True, timeout=45, **options)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Backend startup failed" in output
    assert "Application startup failed" in output
    for private in ("Traceback", str(backend.parent), str(tmp_path), "logging-test-secret"):
        assert private not in output
