"""AFN-039: Backend integration tests with real-mode multimodal loader, parity, and errors.

Separates two test groups clearly:
1. Fixture-backed real-mode integration (always runs offline; uses permitted synthetic
   dataset/images and FakeImageEncoder — NEVER counts as real candidate acceptance).
2. Candidate-backed real-mode integration (runs automatically when the real candidate
   multimodal bundle ``backend/artifacts/multimodal`` AND the pinned offline CLIP cache
   are both present; skips explicitly otherwise).

No Test split data is ever read; no external AI API is ever called.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import math
import os
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from starlette import formparsers

from app import model_loader
from app.config import IMAGE_MAX_BYTES, REPO_ROOT, Settings
from app.main import create_app
from app.model_bundle import load_bundle
from app.schemas import ErrorResponse, HealthResponse, PredictResponse
from ml.common import load_dataset
from ml.export_artifacts import export_all
from ml.inference_parity import (
    DEFAULT_SCORE_ATOL,
    OfflineReference,
    ParitySample,
    run_parity,
    samples_from_dataset,
)

TOKEN = "integration-test-only-token"
AUTH = {"X-Demo-Token": TOKEN}
ALLOWED_ORIGIN = "chrome-extension://" + "c" * 32
DISALLOWED_ORIGIN = "https://untrusted.example"
SYNTHETIC_PNG = REPO_ROOT / "tests" / "fixtures" / "pages" / "synthetic.png"
REAL_CANDIDATE_DIR = REPO_ROOT / "backend" / "artifacts" / "multimodal"
CLIP_REF_PATH = REPO_ROOT / "configs" / "clip-reference.json"


def _make_png(size=(48, 36), mode="RGB", color=(40, 120, 200), **save_kwargs) -> bytes:
    with Image.new(mode, size, color) as img, BytesIO() as buf:
        img.save(buf, format="PNG", **save_kwargs)
        return buf.getvalue()


def _make_exif_jpeg(size=(64, 40), orientation=6) -> bytes:
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    arr[:, : size[0] // 2] = (200, 50, 40)
    arr[:, size[0] // 2 :] = (30, 80, 190)
    exif = Image.Exif()
    exif[0x0112] = orientation
    with Image.fromarray(arr) as img, BytesIO() as buf:
        img.save(buf, format="JPEG", quality=92, exif=exif)
        return buf.getvalue()


def _make_rgba_png(size=(48, 48)) -> bytes:
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[8:40, 8:40] = (180, 40, 40, 255)
    with Image.fromarray(arr, mode="RGBA") as img, BytesIO() as buf:
        img.save(buf, format="PNG")
        return buf.getvalue()


def _real_candidate_and_clip_available() -> tuple[bool, str]:
    meta_path = REAL_CANDIDATE_DIR / "metadata.json"
    if not meta_path.is_file():
        return False, "real multimodal candidate bundle not present at backend/artifacts/multimodal"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("is_fixture") is not False:
        return False, "bundle at backend/artifacts/multimodal is marked as fixture"
    ref = json.loads(CLIP_REF_PATH.read_text(encoding="utf-8"))
    env_home = os.environ.get(ref["runtime"]["cache_env"])
    hub = Path(env_home) / "hub" if env_home else REPO_ROOT / ref["runtime"]["default_cache_dir"] / "hub"
    snap = hub / ("models--" + ref["encoder"]["repo_id"].replace("/", "--")) / "snapshots" / ref["encoder"]["revision"]
    if not all((snap / fname).is_file() for fname in ref["encoder"]["files"]):
        return False, "pinned offline CLIP cache files not present"
    return True, ""


def _post_predict(client: TestClient, *, request_id: str | None = None, title: str | None = None,
                  text: str = "Synthetic English news report with enough clean words for inference.",
                  image_bytes: bytes | None = None, mime: str = "image/png",
                  filename: str = "article.png", headers: dict[str, str] | None = None):
    data: dict[str, str] = {"request_id": request_id or str(uuid4()), "text": text}
    if title is not None:
        data["title"] = title
    raw = SYNTHETIC_PNG.read_bytes() if image_bytes is None else image_bytes
    hdrs = AUTH if headers is None else headers
    return client.post("/predict", headers=hdrs, data=data, files={"image": (filename, raw, mime)})


@pytest.fixture
def fixture_bundle_env(tmp_path, ml_fixture, ml_config, fake_encoder, monkeypatch):
    dataset = load_dataset(ml_fixture["manifest"], ml_fixture["split"], ml_fixture["image_root"])
    export_dir = tmp_path / "bundles"
    export_all(
        dataset,
        ml_config,
        fake_encoder,
        export_dir,
        inputs={
            "manifest_sha256": dataset.manifest_sha256,
            "split_sha256": dataset.split_sha256,
            "experiment_config_sha256": "0" * 64,
        },
    )
    fake_encoder.calls = 0
    closed = []
    encode = fake_encoder.encode
    monkeypatch.setattr(fake_encoder, "encode", lambda images: encode(images).astype(np.float32))
    monkeypatch.setattr(fake_encoder, "close", lambda: closed.append(True), raising=False)
    monkeypatch.setattr(model_loader, "ClipImageEncoder", lambda *, offline: fake_encoder)
    return export_dir / "multimodal", dataset, fake_encoder, closed


# ---------------------------------------------------------------------------
# 1. Fixture-backed real-mode integration (always runs offline)
# ---------------------------------------------------------------------------


def test_fixture_http_predict_matches_offline_parity_and_edge_cases(fixture_bundle_env, monkeypatch):
    bundle_dir, dataset, encoder, closed = fixture_bundle_env

    def forbid_fit(*args, **kwargs):
        pytest.fail("Inference must never fit CountVectorizer or LogisticRegression")

    monkeypatch.setattr(CountVectorizer, "fit", forbid_fit)
    monkeypatch.setattr(LogisticRegression, "fit", forbid_fit)

    bundle = load_bundle(bundle_dir, expected_configuration="multimodal")
    val_samples = samples_from_dataset(dataset.rows("validation"))
    extra_samples = [
        ParitySample("edge-exif", "Rotated photo report", "Official report on local transit expansion.", _make_exif_jpeg()),
        ParitySample("edge-rgba", None, "Short transparent image test article.", _make_rgba_png()),
        ParitySample("edge-truncate", "Long body", " ".join(["policy"] * 1800), _make_png()),
    ]
    all_samples = [*val_samples, *extra_samples]

    # End-to-end HTTP /predict parity against OfflineReference
    offline = OfflineReference(bundle, encoder, batch_size=16)
    off_scores, off_labels, off_trunc = offline.score(all_samples)

    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            predictor_mode="real",
            demo_token=TOKEN,
            extension_origin=ALLOWED_ORIGIN,
            model_artifact_path=bundle_dir,
        )
    )
    with TestClient(app) as client:
        health = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
        assert health.status_code == 200
        assert HealthResponse.model_validate(health.json()).model_ready is True
        assert health.headers["X-AFN-Inference-Mode"] == "real"
        assert health.headers["X-AFN-Model-State"] == "ready"
        assert health.headers["access-control-allow-origin"] == ALLOWED_ORIGIN

        report = run_parity(bundle, app.state.inference_adapter, all_samples, encoder=encoder, atol=DEFAULT_SCORE_ATOL)
        assert report.passed, report.failures
        assert report.max_abs_score_diff is not None and report.max_abs_score_diff <= DEFAULT_SCORE_ATOL
        assert report.labels_equal and report.truncated_equal and report.identity_equal and report.n_errors == 0

        for sample, exp_score, exp_label, exp_trunc in zip(all_samples, off_scores, off_labels, off_trunc, strict=True):
            req_id = str(uuid4())
            mime = "image/jpeg" if sample.sample_id == "edge-exif" else "image/png"
            resp = _post_predict(
                client,
                request_id=req_id,
                title=sample.title,
                text=sample.body,
                image_bytes=sample.image_bytes,
                mime=mime,
                headers={**AUTH, "Origin": ALLOWED_ORIGIN},
            )
            assert resp.status_code == 200
            assert resp.headers["X-AFN-Inference-Mode"] == "real"
            assert resp.headers["X-AFN-Model-State"] == "ready"
            assert resp.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
            parsed = PredictResponse.model_validate(resp.json())
            assert parsed.request_id == UUID(req_id)
            assert math.isfinite(parsed.fake_score) and 0.0 <= parsed.fake_score <= 1.0
            assert abs(parsed.fake_score - float(exp_score)) <= DEFAULT_SCORE_ATOL
            assert parsed.label == exp_label
            assert parsed.text_truncated is bool(exp_trunc)
            assert parsed.model_id == bundle.model_id
            assert parsed.model_version == bundle.model_version
            assert parsed.processing_time_ms >= 0

    assert app.state.predictor is None
    assert closed  # Encoder close() invoked on shutdown


def test_fixture_contract_error_matrix_and_resource_cleanup(fixture_bundle_env, monkeypatch):
    bundle_dir, _, _, _ = fixture_bundle_env
    spooled_files = []
    orig_spooled = formparsers.SpooledTemporaryFile

    def track_spooled(*args, **kwargs):
        f = orig_spooled(*args, **kwargs)
        spooled_files.append(f)
        return f

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", track_spooled)

    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            predictor_mode="real",
            demo_token=TOKEN,
            extension_origin=ALLOWED_ORIGIN,
            model_artifact_path=bundle_dir,
        )
    )
    with TestClient(app) as client:
        # 401: missing / wrong token (even from allowed CORS origin)
        r_unauth = _post_predict(client, headers={"Origin": ALLOWED_ORIGIN})
        assert r_unauth.status_code == 401
        assert ErrorResponse.model_validate(r_unauth.json()).error_code == "invalid_token"
        assert r_unauth.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

        # Disallowed origin gets no CORS allow header on preflight or error
        r_preflight_bad = client.options(
            "/predict",
            headers={
                "Origin": DISALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Demo-Token",
            },
        )
        assert r_preflight_bad.status_code == 400
        assert "access-control-allow-origin" not in r_preflight_bad.headers

        # 400: invalid UUID, blank text, URL-only text (empty after preprocess_text), MIME mismatch, corrupt image
        req_id = str(uuid4())
        bad_cases = [
            _post_predict(client, request_id="bad-uuid"),
            _post_predict(client, request_id=req_id, text="   \n\t  "),
            _post_predict(client, request_id=req_id, text="https://example.test/only-url"),
            _post_predict(client, request_id=req_id, title="t" * 501),
            _post_predict(client, request_id=req_id, text="a" * 50_001),
            _post_predict(client, request_id=req_id, image_bytes=_make_png(), mime="image/jpeg"),
            _post_predict(client, request_id=req_id, image_bytes=b"not-a-valid-png", mime="image/png"),
            client.post("/predict", headers=AUTH, json={"request_id": req_id, "text": "json rejected"}),
        ]
        for resp in bad_cases:
            assert resp.status_code == 400
            err = ErrorResponse.model_validate(resp.json())
            assert err.error_code == "invalid_input"
            assert TOKEN not in resp.text and str(bundle_dir) not in resp.text

        # 413: file > 10 MiB
        oversize_resp = _post_predict(
            client,
            request_id=str(uuid4()),
            image_bytes=b"x" * (IMAGE_MAX_BYTES + 1),
            mime="image/png",
        )
        assert oversize_resp.status_code == 413
        assert ErrorResponse.model_validate(oversize_resp.json()).error_code == "request_too_large"

        # Service remains ready and healthy after all client 400/401/413 errors
        assert client.get("/health").json()["model_ready"] is True
        ok_resp = _post_predict(client)
        assert ok_resp.status_code == 200

    assert spooled_files and all(f.closed for f in spooled_files)


def test_fixture_demo_scale_multiple_and_concurrent_requests(fixture_bundle_env):
    bundle_dir, _, _, _ = fixture_bundle_env
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            predictor_mode="real",
            demo_token=TOKEN,
            model_artifact_path=bundle_dir,
        )
    )
    fixed_img = _make_png()
    fixed_text = "Official committee releases annual public infrastructure budget report."

    with TestClient(app) as client:
        scores = []
        # 10 sequential requests interleaved with 400 errors
        for idx in range(10):
            if idx % 3 == 0:
                bad = _post_predict(client, text="https://only-url.example")
                assert bad.status_code == 400
            rid = str(uuid4())
            resp = _post_predict(client, request_id=rid, text=fixed_text, image_bytes=fixed_img)
            assert resp.status_code == 200
            payload = PredictResponse.model_validate(resp.json())
            assert payload.request_id == UUID(rid)
            scores.append(payload.fake_score)

        # Deterministic identical predictions across repeated requests
        assert all(s == scores[0] for s in scores)

        # Concurrent demo-scale burst (4 threads)
        def worker(_):
            rid = str(uuid4())
            r = _post_predict(client, request_id=rid, text=fixed_text, image_bytes=fixed_img)
            return r.status_code, r.json(), rid

        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(worker, range(8)))
        for status, body, rid in outcomes:
            assert status == 200
            parsed = PredictResponse.model_validate(body)
            assert parsed.request_id == UUID(rid)
            assert parsed.fake_score == scores[0]


def test_startup_partial_failure_disposes_encoder_and_serves_503(fixture_bundle_env, monkeypatch):
    bundle_dir, _, encoder, closed = fixture_bundle_env

    def fail_warmup(images):
        raise RuntimeError(f"Secret path {bundle_dir} token {TOKEN}")

    monkeypatch.setattr(encoder, "encode", fail_warmup)
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            predictor_mode="real",
            demo_token=TOKEN,
            model_artifact_path=bundle_dir,
        )
    )
    with TestClient(app) as client:
        assert closed  # Encoder was disposed on warm-up failure
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["model_ready"] is False
        assert health.headers["X-AFN-Model-State"] == "error"
        assert health.headers["X-AFN-Inference-Mode"] == "real"

        rid = str(uuid4())
        resp = _post_predict(client, request_id=rid)
        assert resp.status_code == 503
        assert resp.json() == {
            "detail": "Model is not ready",
            "error_code": "model_not_ready",
            "request_id": rid,
        }
        assert str(bundle_dir) not in health.text + resp.text
        assert TOKEN not in health.text + resp.text


# ---------------------------------------------------------------------------
# 2. Real candidate + real offline CLIP integration (auto-runs when present)
# ---------------------------------------------------------------------------


_REAL_OK, _REAL_SKIP_REASON = _real_candidate_and_clip_available()


@pytest.mark.skipif(not _REAL_OK, reason=_REAL_SKIP_REASON)
def test_real_candidate_multimodal_http_parity_and_demo_burst():
    """End-to-end verification with the real candidate bundle and offline CLIP."""
    bundle = load_bundle(REAL_CANDIDATE_DIR, expected_configuration="multimodal")
    assert bundle.metadata["is_fixture"] is False
    assert not bundle.model_id.endswith("-fixture")
    assert not bundle.model_version.endswith("-fixture")

    samples = [
        ParitySample(
            "synth-short-png",
            "City council approves transit budget",
            "The city council approved the annual public transit maintenance budget on Tuesday after public hearings.",
            SYNTHETIC_PNG.read_bytes(),
        ),
        ParitySample(
            "synth-exif-jpeg",
            "Shocking secret miracle exposed",
            "Unverified social media posts claim an overnight miracle cure was hidden from everyone.",
            _make_exif_jpeg(),
        ),
        ParitySample(
            "synth-rgba-truncated",
            None,
            " ".join(["report"] * 1700),
            _make_rgba_png(),
        ),
    ]

    settings = Settings(
        _env_file=None,
        environment="demo",
        predictor_mode="real",
        demo_token=TOKEN,
        extension_origin=ALLOWED_ORIGIN,
        model_artifact_path=REAL_CANDIDATE_DIR,
    )
    predictor = model_loader.load_predictor(settings)
    try:
        parity = run_parity(bundle, predictor, samples, encoder=predictor._encoder, atol=DEFAULT_SCORE_ATOL)
        assert parity.passed, parity.failures
        assert parity.max_abs_score_diff is not None and parity.max_abs_score_diff <= DEFAULT_SCORE_ATOL
        assert parity.labels_equal and parity.truncated_equal and parity.identity_equal
        assert parity.n_errors == 0
    finally:
        predictor.close()

    # Run full FastAPI service in demo/real mode with real candidate + CORS + token
    app = create_app(settings)
    with TestClient(app) as client:
        health = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
        assert health.status_code == 200
        assert health.json() == {
            "service_status": "ok",
            "model_ready": True,
            "contract_version": "0.2.0",
        }
        assert health.headers["X-AFN-Inference-Mode"] == "real"
        assert health.headers["X-AFN-Model-State"] == "ready"
        assert health.headers["access-control-allow-origin"] == ALLOWED_ORIGIN

        # Verify real candidate predictions across permitted synthetic cases
        seen_results = []
        for sample in samples:
            rid = str(uuid4())
            mime = "image/jpeg" if sample.sample_id == "synth-exif-jpeg" else "image/png"
            resp = _post_predict(
                client,
                request_id=rid,
                title=sample.title,
                text=sample.body,
                image_bytes=sample.image_bytes,
                mime=mime,
                headers={**AUTH, "Origin": ALLOWED_ORIGIN},
            )
            assert resp.status_code == 200
            parsed = PredictResponse.model_validate(resp.json())
            assert parsed.request_id == UUID(rid)
            assert math.isfinite(parsed.fake_score) and 0.0 <= parsed.fake_score <= 1.0
            assert parsed.label == ("fake" if parsed.fake_score >= bundle.threshold else "real")
            assert parsed.model_id == bundle.model_id
            assert parsed.model_version == bundle.model_version
            assert parsed.processing_time_ms >= 0
            seen_results.append(parsed)

        assert seen_results[0].text_truncated is False
        assert seen_results[2].text_truncated is True

        # Interleaved error check: 401 and 400 do not degrade real model readiness
        assert _post_predict(client, headers={}).status_code == 401
        assert _post_predict(client, text="https://only-url.example").status_code == 400
        assert client.get("/health").json()["model_ready"] is True

        # Repeated inference consistency after errors
        rid_repeat = str(uuid4())
        repeat = _post_predict(
            client,
            request_id=rid_repeat,
            title=samples[0].title,
            text=samples[0].body,
            image_bytes=samples[0].image_bytes,
            mime="image/png",
        )
        assert repeat.status_code == 200
        assert abs(repeat.json()["fake_score"] - seen_results[0].fake_score) <= DEFAULT_SCORE_ATOL

    assert app.state.predictor is None
    assert not app.state.inference_adapter.ready
