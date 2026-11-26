"""AFN-038: CORS policy, preflight, token independence, and error sanitization."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from conftest import AUTH, REQUEST_ID, TOKEN, png_bytes, valid_post
from app.config import Settings
from app.main import create_app

ALLOWED_ORIGIN = "chrome-extension://" + "a" * 32
OTHER_EXTENSION = "chrome-extension://" + "b" * 32


def make_app(*, origin=ALLOWED_ORIGIN, mode="mock", environment="test", demo_token=TOKEN):
    return create_app(
        Settings(
            _env_file=None,
            environment=environment,
            predictor_mode=mode,
            demo_token=demo_token,
            extension_origin=origin,
        )
    )


def test_allowed_origin_preflight_and_predict_flow():
    with TestClient(make_app()) as client:
        preflight = client.options(
            "/predict",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Demo-Token, Content-Type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
        assert "POST" in preflight.headers.get("access-control-allow-methods", "")
        allowed_headers = preflight.headers.get("access-control-allow-headers", "").lower()
        assert "x-demo-token" in allowed_headers
        assert "content-type" in allowed_headers
        assert preflight.headers.get("access-control-allow-credentials") is None

        health = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
        assert health.status_code == 200
        assert health.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
        exposed = health.headers.get("access-control-expose-headers", "")
        assert "X-AFN-Inference-Mode" in exposed
        assert "X-AFN-Model-State" in exposed

        response = client.post(
            "/predict",
            headers={**AUTH, "Origin": ALLOWED_ORIGIN},
            data={"request_id": REQUEST_ID, "text": "Synthetic article"},
            files={"image": ("test.png", png_bytes(), "image/png")},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
        assert response.headers["X-AFN-Inference-Mode"] == "mock"
        assert response.headers["X-AFN-Model-State"] == "ready"
        assert "X-AFN-Inference-Mode" in response.headers.get("access-control-expose-headers", "")


def test_allowed_origin_still_requires_token_and_can_read_contract_errors():
    with TestClient(make_app(mode="real", environment="demo")) as client:
        unauth = client.post(
            "/predict",
            headers={"Origin": ALLOWED_ORIGIN},
            data={"request_id": REQUEST_ID, "text": "Synthetic article"},
            files={"image": ("test.png", png_bytes(), "image/png")},
        )
        assert unauth.status_code == 401
        assert unauth.json()["error_code"] == "invalid_token"
        assert unauth.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

        bad_input = client.post(
            "/predict",
            headers={**AUTH, "Origin": ALLOWED_ORIGIN},
            data={"request_id": "not-a-uuid", "text": "Synthetic article"},
            files={"image": ("test.png", png_bytes(), "image/png")},
        )
        assert bad_input.status_code == 400
        assert bad_input.json()["error_code"] == "invalid_input"
        assert bad_input.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

        not_ready = client.post(
            "/predict",
            headers={**AUTH, "Origin": ALLOWED_ORIGIN},
            data={"request_id": str(uuid4()), "text": "Synthetic article"},
            files={"image": ("test.png", png_bytes(), "image/png")},
        )
        assert not_ready.status_code == 503
        assert not_ready.json()["error_code"] == "model_not_ready"
        assert not_ready.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@pytest.mark.parametrize(
    "bad_origin",
    [
        OTHER_EXTENSION,
        "https://evil.example",
        "http://127.0.0.1:8000",
        "null",
    ],
)
def test_disallowed_origin_receives_no_cors_grant(bad_origin):
    with TestClient(make_app()) as client:
        preflight = client.options(
            "/predict",
            headers={
                "Origin": bad_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Demo-Token",
            },
        )
        assert preflight.status_code == 400
        assert "access-control-allow-origin" not in preflight.headers

        health = client.get("/health", headers={"Origin": bad_origin})
        assert health.status_code == 200
        assert "access-control-allow-origin" not in health.headers

        unauth = client.post("/predict", headers={"Origin": bad_origin})
        assert unauth.status_code == 401
        assert "access-control-allow-origin" not in unauth.headers

        # Non-browser HTTP client with valid token still gets no CORS allow header.
        authed = client.post(
            "/predict",
            headers={**AUTH, "Origin": bad_origin},
            data={"request_id": REQUEST_ID, "text": "Synthetic article"},
            files={"image": ("test.png", png_bytes(), "image/png")},
        )
        assert authed.status_code == 200
        assert "access-control-allow-origin" not in authed.headers


def test_unconfigured_extension_origin_denies_all_cors_grants():
    with TestClient(make_app(origin=None)) as client:
        preflight = client.options(
            "/predict",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Demo-Token",
            },
        )
        assert preflight.status_code == 400
        assert "access-control-allow-origin" not in preflight.headers

        health = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
        assert health.status_code == 200
        assert "access-control-allow-origin" not in health.headers


@pytest.mark.parametrize(
    "method,headers",
    [
        ("DELETE", "X-Demo-Token"),
        ("POST", "X-Unexpected-Header"),
    ],
)
def test_preflight_rejects_disallowed_method_or_header(method, headers):
    with TestClient(make_app()) as client:
        preflight = client.options(
            "/predict",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": headers,
            },
        )
        assert preflight.status_code == 400


def test_no_origin_non_browser_client_still_enforces_token():
    with TestClient(make_app()) as client:
        assert client.post("/predict").status_code == 401
        assert valid_post(client).status_code == 200
