import json

import anyio
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.predictor import ModelNotReadyError, get_predictor


def make_app(**settings):
    return create_app(Settings(_env_file=None, **settings))


def test_lifecycle_starts_without_artifacts_and_cleans_up(tmp_path):
    missing = tmp_path / "missing-model"
    app = make_app(model_artifact_path=missing, demo_token="test-only-secret")
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "service_status": "ok", "model_ready": False, "contract_version": "0.1.0"
        }
        assert str(missing) not in health.text
        assert "test-only-secret" not in health.text
        assert app.state.predictor is None
        assert app.state.settings.model_artifact_path == missing
    assert app.state.predictor is None
    assert app.state.settings is None
    assert not missing.exists()


@pytest.mark.parametrize("body,headers", [
    (b"", {}),
    (b'{"request_id":"bad","text":"private article"}', {"content-type": "application/json"}),
    (b"broken multipart", {"content-type": "multipart/form-data; boundary=missing"}),
    (b"", {"X-Demo-Token": "test-only-invalid"}),
])
def test_prediction_is_disabled_for_all_unparsed_inputs(body, headers):
    with TestClient(make_app()) as client:
        response = client.post("/predict", content=body, headers=headers)
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Model is not ready", "error_code": "model_not_ready", "request_id": None
        }


def test_predict_does_not_read_asgi_body():
    async def run():
        app = make_app()
        sent = []

        async def receive():
            raise AssertionError("Disabled prediction must not read upload bytes")

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "POST", "scheme": "http", "path": "/predict", "root_path": "",
            "raw_path": b"/predict", "query_string": b"", "headers": [],
            "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 8000),
        }
        async with app.router.lifespan_context(app):
            await app(scope, receive, send)
        assert sent[0]["status"] == 503
        assert json.loads(sent[1]["body"])["request_id"] is None

    anyio.run(run)


def test_di_provider_and_override_do_not_enable_predictions():
    app = make_app()
    sentinel = object()  # No mock Predictor and no generated result.

    @app.get("/test-di", include_in_schema=False)
    def probe(provider=Depends(get_predictor)):
        return {"same": provider is sentinel}

    with TestClient(app) as client:
        assert client.get("/test-di").status_code == 503
        app.state.predictor = sentinel
        assert client.get("/test-di").json() == {"same": True}
        app.state.predictor = None
        app.dependency_overrides[get_predictor] = lambda: sentinel
        assert client.get("/test-di").json() == {"same": True}
        assert client.post("/predict").status_code == 503
        assert client.get("/health").json()["model_ready"] is False


def test_model_failure_details_are_not_returned():
    app = make_app()

    def unavailable():
        raise ModelNotReadyError("test-only-secret /private/model/path private article")

    app.dependency_overrides[get_predictor] = unavailable
    with TestClient(app) as client:
        response = client.post("/predict")
        assert response.status_code == 503
        assert "private" not in response.text
        assert "test-only-secret" not in response.text


def test_openapi_describes_only_implemented_behavior():
    with TestClient(make_app()) as client:
        schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/predict"]["post"]
    assert "503" in operation["responses"]
    assert "200" not in operation["responses"]
    assert "422" not in operation["responses"]
    assert "requestBody" not in operation


def test_app_instances_do_not_share_provider_state():
    first, second = make_app(), make_app()
    with TestClient(first), TestClient(second):
        first.state.predictor = object()
        assert second.state.predictor is None
