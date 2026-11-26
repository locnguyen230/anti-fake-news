import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

from app import model_loader
from app.config import Settings
from app.main import create_app
from ml.common import load_dataset
from ml.export_artifacts import export_all


IMAGE = Path(__file__).parent / "fixtures" / "pages" / "synthetic.png"
TOKEN = "loader-test-only"


def test_parity_factory_uses_serving_loader_and_ignores_deployment_settings(bundle, monkeypatch):
    from ml.inference_parity import resolve_factory
    from app.predictor import PredictorInput

    path, encoder, constructors = bundle
    monkeypatch.setenv("AFN_ENVIRONMENT", "production")
    monkeypatch.setenv("AFN_PREDICTOR_MODE", "mock")
    monkeypatch.setenv("AFN_MODEL_METADATA_SHA256", "0" * 64)
    factory = resolve_factory("app.predictor:load_for_parity")
    predictor = factory(path, None, None)
    try:
        assert constructors == [True] and encoder.calls == 1  # offline + serving warm-up
        result = predictor.predict(PredictorInput(request_id=uuid4(), text="Synthetic news article",
                                                   image_bytes=IMAGE.read_bytes()))
        assert result.model_id.endswith("-fixture")
    finally:
        predictor.close()
    assert predictor._bundle is None and predictor._encoder is None


@pytest.fixture
def bundle(tmp_path, ml_fixture, ml_config, fake_encoder, monkeypatch):
    dataset = load_dataset(ml_fixture["manifest"], ml_fixture["split"], ml_fixture["image_root"])
    export_dir = tmp_path / "bundles"
    export_all(dataset, ml_config, fake_encoder, export_dir, inputs={
        "manifest_sha256": dataset.manifest_sha256,
        "split_sha256": dataset.split_sha256,
        "experiment_config_sha256": "0" * 64,
    })
    fake_encoder.calls = 0
    constructors = []
    encode = fake_encoder.encode
    monkeypatch.setattr(fake_encoder, "encode", lambda images: encode(images).astype(np.float32))

    def encoder(*, offline):
        constructors.append(offline)
        return fake_encoder

    monkeypatch.setattr(model_loader, "ClipImageEncoder", encoder)
    return export_dir / "multimodal", fake_encoder, constructors


def service(path, environment="test"):
    return create_app(Settings(_env_file=None, environment=environment, predictor_mode="real",
                               model_artifact_path=path, demo_token=TOKEN))


def test_restart_recovers_from_inference_failure_without_reusing_closed_provider(bundle, monkeypatch):
    path, encoder, constructors = bundle
    encode = encoder.encode
    app = service(path)
    with TestClient(app) as client:
        first_provider = app.state.inference_adapter._predictor
        assert predict(client, str(uuid4())).status_code == 200

        def fail(images):
            raise RuntimeError("private runtime failure")

        monkeypatch.setattr(encoder, "encode", fail)
        assert predict(client, str(uuid4())).status_code == 503
        assert not client.get("/health").json()["model_ready"]
        assert first_provider._bundle is None and first_provider._encoder is None
    assert app.state.predictor is None
    monkeypatch.setattr(encoder, "encode", encode)
    with TestClient(app) as client:
        assert app.state.inference_adapter._predictor is not first_provider
        assert client.get("/health").json()["model_ready"]
        assert predict(client, str(uuid4())).status_code == 200
    assert constructors == [True, True]


def predict(client, request_id, text="Synthetic news article"):
    return client.post("/predict", headers={"X-Demo-Token": TOKEN},
                       data={"request_id": request_id, "text": text},
                       files={"image": ("test.png", IMAGE.read_bytes(), "image/png")})


def test_one_startup_load_and_warmup_for_multiple_predictions(bundle, monkeypatch):
    path, encoder, constructors = bundle
    load_bundle = model_loader.load_bundle
    loads = []

    def counted_load(*args, **kwargs):
        loads.append(args[0])
        return load_bundle(*args, **kwargs)

    def unexpected_fit(*args, **kwargs):
        pytest.fail("a fitted bundle must not fit during serving")

    monkeypatch.setattr(model_loader, "load_bundle", counted_load)
    monkeypatch.setattr(CountVectorizer, "fit", unexpected_fit)
    monkeypatch.setattr(LogisticRegression, "fit", unexpected_fit)
    app = service(path)
    assert not loads and not constructors
    with TestClient(app) as client:
        assert client.get("/health").json()["model_ready"] is True
        assert constructors == [True] and encoder.calls == 1
        for _ in range(2):
            request_id = str(uuid4())
            response = predict(client, request_id)
            assert response.status_code == 200
            assert response.headers["X-AFN-Inference-Mode"] == "real"
            result = response.json()
            assert result["request_id"] == request_id and result["model_id"].endswith("-fixture")
            assert 0 <= result["fake_score"] <= 1
        assert loads == [path] and constructors == [True] and encoder.calls == 3
        request_id = str(uuid4())
        response = predict(client, request_id, "https://example.test/only-a-url")
        assert response.status_code == 400 and response.json()["request_id"] == request_id
        assert client.get("/health").json()["model_ready"] is True
    assert app.state.predictor is None and not app.state.inference_adapter.ready


@pytest.mark.parametrize("failure", [
    "missing", "schema", "date", "version", "dimensions", "classes", "mapping", "checksum",
    "encoder", "encoder-dimension", "embedding-dtype", "warmup", "demo",
])
def test_failed_startup_is_sanitized_and_never_installs_mock(bundle, failure, monkeypatch):
    path, encoder, _ = bundle
    metadata_path = path / "metadata.json"
    if failure == "missing":
        metadata_path.unlink()
    elif failure == "checksum":
        with (path / "classifier" / "coef.npy").open("ab") as handle:
            handle.write(b"changed")
    elif failure == "encoder":
        encoder.identity["revision"] = "mismatched-checkpoint"
    elif failure == "encoder-dimension":
        encoder.dim += 1
    elif failure == "embedding-dtype":
        monkeypatch.setattr(encoder, "encode", lambda images: np.ones((1, encoder.dim), dtype=np.float64))
    elif failure == "warmup":
        def fail_encode(images):
            raise RuntimeError(f"Private path {path} and token {TOKEN}")

        monkeypatch.setattr(encoder, "encode", fail_encode)
    elif failure in {"schema", "date", "version", "dimensions", "classes", "mapping"}:
        metadata = json.loads(metadata_path.read_bytes())
        if failure == "schema":
            metadata.pop("training")
        elif failure == "date":
            metadata["created_at"] = "invalid-date"
        elif failure == "version":
            metadata["preprocess_version"] = "unsupported-version"
        elif failure == "dimensions":
            metadata["image"]["dim"] += 1
        elif failure == "classes":
            metadata["classes"] = [0, 0]
        else:
            metadata["label_map"] = {"0": "real", "1": "real"}
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with TestClient(service(path, "demo" if failure == "demo" else "test")) as client:
        health = client.get("/health")
        assert health.json()["model_ready"] is False and health.headers["X-AFN-Model-State"] == "error"
        request_id = str(uuid4())
        response = predict(client, request_id)
        assert response.status_code == 503 and response.headers["X-AFN-Inference-Mode"] == "real"
        assert response.json() == {"error_code": "model_not_ready", "detail": "Model is not ready",
                                   "request_id": request_id}
        assert str(path) not in health.text + response.text and TOKEN not in health.text + response.text


@pytest.mark.parametrize(("artifact", "allow_candidate", "ready"), [
    ("missing", True, False),
    ("fixture", True, False),
    ("candidate", False, False),
    ("candidate", True, True),
    ("wrong-digest", True, False),
    ("frozen", False, True),
])
def test_production_requires_a_pinned_real_bundle(bundle, artifact, allow_candidate, ready):
    path, _, constructors = bundle
    metadata_path = path / "metadata.json"
    metadata = json.loads(metadata_path.read_bytes())
    if artifact in ("candidate", "wrong-digest", "frozen"):
        metadata.update(
            is_fixture=False,
            evidence_kind="VALIDATION_ONLY",
            model_id=metadata["model_id"].removesuffix("-fixture"),
            model_version=metadata["model_version"].removesuffix("-fixture"),
            status="frozen" if artifact == "frozen" else "candidate",
        )
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    digest = sha256(metadata_path.read_bytes()).hexdigest().upper()
    if artifact == "wrong-digest":
        digest = "0" * 64
    if artifact == "missing":
        metadata_path.unlink()
    app = create_app(Settings(
        _env_file=None, environment="production", demo_token=TOKEN,
        model_artifact_path=path, model_metadata_sha256=digest,
        allow_candidate_model=allow_candidate,
    ))
    if not ready:
        with pytest.raises(RuntimeError, match="Production startup failed"):
            with TestClient(app):
                pytest.fail("The server must not start with an invalid production artifact")
        assert constructors == []
        return

    with TestClient(app) as client:
        assert client.get("/health").json()["model_ready"] is True
        response = predict(client, str(uuid4()))
        assert response.status_code == 200
        assert response.headers["X-AFN-Inference-Mode"] == "real"
        assert response.json()["model_version"] == metadata["model_version"]
