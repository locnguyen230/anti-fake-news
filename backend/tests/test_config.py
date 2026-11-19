import pytest
from pydantic import ValidationError

from app.config import IMAGE_MAX_BYTES, REPO_ROOT, Settings


def test_defaults_require_no_credentials_or_artifacts():
    settings = Settings(_env_file=None)
    assert (settings.host, settings.port) == ("127.0.0.1", 8000)
    assert settings.demo_token is None
    assert settings.environment == "demo"
    assert settings.predictor_mode == "real"
    assert settings.extension_origin is None
    assert settings.model_artifact_path == REPO_ROOT / "artifacts" / "model"
    assert settings.max_request_bytes > IMAGE_MAX_BYTES


def test_env_file_and_environment_precedence(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AFN_HOST=::1\nAFN_PORT=8001\nAFN_DEMO_TOKEN=test-only-not-a-secret\n"
        "AFN_EXTENSION_ORIGIN=chrome-extension://" + "a" * 32 + "\n"
        "AFN_MODEL_ARTIFACT_PATH=artifacts/test-only\nAFN_MAX_REQUEST_BYTES=14000000\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AFN_PORT", "8123")
    settings = Settings(_env_file=env_file)
    assert settings.host == "::1"
    assert settings.port == 8123
    assert settings.demo_token.get_secret_value() == "test-only-not-a-secret"
    assert settings.extension_origin == "chrome-extension://" + "a" * 32
    assert settings.model_artifact_path == REPO_ROOT / "artifacts" / "test-only"
    assert settings.max_request_bytes == 14_000_000
    assert "test-only-not-a-secret" not in repr(settings)
    assert "test-only-not-a-secret" not in settings.model_dump_json()


def test_example_is_loadable_from_another_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=REPO_ROOT / ".env.example")
    assert settings.demo_token is None
    assert settings.extension_origin is None
    assert settings.model_artifact_path == REPO_ROOT / "artifacts" / "model"
    assert Settings.model_config["env_file"] == REPO_ROOT / ".env"


@pytest.mark.parametrize("overrides", [
    {"host": "0.0.0.0"}, {"host": "192.168.1.2"},
    {"port": 0}, {"port": 65536},
    {"max_request_bytes": IMAGE_MAX_BYTES},
    {"extension_origin": "*"}, {"extension_origin": "https://example.com"},
    {"extension_origin": "chrome-extension://" + "a" * 32 + "/path"},
])
def test_rejects_unsafe_or_invalid_configuration(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_absolute_artifact_path_preserved(tmp_path):
    assert Settings(_env_file=None, model_artifact_path=tmp_path).model_artifact_path == tmp_path


def test_launcher_uses_configured_bind_without_starting_server(monkeypatch):
    from app import __main__ as launcher

    calls = []
    monkeypatch.setenv("AFN_HOST", "127.0.0.1")
    monkeypatch.setenv("AFN_PORT", "8123")
    monkeypatch.setattr(launcher, "Settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(launcher.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    launcher.main()
    assert calls == [(("app.main:app",), {
        "host": "127.0.0.1", "port": 8123, "access_log": False,
    })]


def test_launcher_reports_config_failure_without_input(monkeypatch):
    from app import __main__ as launcher

    monkeypatch.setenv("AFN_PORT", "private-invalid-value")
    monkeypatch.setattr(launcher, "Settings", lambda: Settings(_env_file=None))
    with pytest.raises(SystemExit) as error:
        launcher.main()
    assert "private-invalid-value" not in str(error.value)
    assert str(error.value).startswith("Invalid AFN configuration")


@pytest.mark.parametrize("environment", ["dev", "test"])
def test_mock_requires_both_environment_and_mode(monkeypatch, environment):
    monkeypatch.setenv("AFN_ENVIRONMENT", environment)
    assert Settings(_env_file=None).predictor_mode == "real"
    monkeypatch.setenv("AFN_PREDICTOR_MODE", "mock")
    assert Settings(_env_file=None).predictor_mode == "mock"


@pytest.mark.parametrize("overrides", [
    {"predictor_mode": "mock"},
    {"environment": "demo", "predictor_mode": "mock"},
    {"environment": "production", "predictor_mode": "mock"},
    {"environment": "dev", "predictor_mode": "auto"},
])
def test_invalid_or_unsafe_modes_fail_startup_configuration(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)
