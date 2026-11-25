from uuid import UUID

import pytest

from app.config import Settings
from app.dev.mock_predictor import MOCK_MODEL_ID, MockPredictor
from app.inference_adapter import InferenceAdapter, ModelState, create_adapter
from app.predictor import ModelNotReadyError, PredictorInput


def sample_input(text="Mock-only article", image_bytes=b"mock-only bytes"):
    return PredictorInput(request_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                          text=text, image_bytes=image_bytes)


def test_mock_is_fixed_and_does_not_depend_on_input():
    mock = MockPredictor()
    first = mock.predict(sample_input())
    second = mock.predict(sample_input("Different mock article", b"different bytes"))
    assert first == second
    assert first.model_id == MOCK_MODEL_ID
    assert first.model_version.startswith("mock-")
    assert first.label == "real" and first.fake_score == 0.42
    assert first.text_truncated is False


def test_adapter_state_lifecycle():
    adapter = InferenceAdapter(mode="mock")
    assert adapter.state == ModelState.NOT_LOADED and not adapter.ready
    with pytest.raises(ModelNotReadyError):
        adapter.predict(sample_input())
    adapter.initialize(MockPredictor)
    assert adapter.state == ModelState.READY and adapter.ready
    assert adapter.predict(sample_input()).model_id == MOCK_MODEL_ID
    adapter.close()
    adapter.close()  # Cleanup is idempotent.
    assert adapter.state == ModelState.NOT_LOADED and not adapter.ready
    with pytest.raises(ModelNotReadyError):
        adapter.predict(sample_input())


def test_initialization_failure_has_no_fallback_and_requires_explicit_retry():
    adapter = InferenceAdapter(mode="real")

    def failing_factory():
        raise RuntimeError("private-model-path secret-token")

    adapter.initialize(failing_factory)
    assert adapter.mode == "real" and adapter.state == ModelState.ERROR
    with pytest.raises(ModelNotReadyError) as error:
        adapter.predict(sample_input())
    assert str(error.value) == ""
    assert "private-model-path" not in repr(vars(adapter))
    assert not adapter.ready


@pytest.mark.parametrize("failure", [RuntimeError("private input"), ModelNotReadyError("secret")])
def test_prediction_failure_marks_error_and_never_falls_back(failure):
    class FailingPredictor:
        def predict(self, inputs):
            raise failure

    adapter = InferenceAdapter(mode="real")
    adapter.initialize(FailingPredictor)
    with pytest.raises(ModelNotReadyError):
        adapter.predict(sample_input())
    assert adapter.mode == "real"
    assert adapter.state == ModelState.ERROR
    assert not adapter.ready
    with pytest.raises(ModelNotReadyError):
        adapter.predict(sample_input())


def test_invalid_provider_and_output_fail_closed():
    adapter = InferenceAdapter(mode="mock")
    adapter.initialize(lambda: object())
    assert adapter.state == ModelState.ERROR

    class InvalidOutput:
        def predict(self, inputs):
            return {"label": "invented", "fake_score": float("nan")}

    adapter.initialize(InvalidOutput)
    with pytest.raises(ModelNotReadyError):
        adapter.predict(sample_input())
    assert adapter.state == ModelState.ERROR


@pytest.mark.parametrize("artifact_exists", [False, True])
def test_real_factory_never_loads_mock_or_infers_readiness(tmp_path, monkeypatch, artifact_exists):
    from app.dev import mock_predictor

    def must_not_construct():
        raise AssertionError("Real mode must never construct mock")

    monkeypatch.setattr(mock_predictor, "MockPredictor", must_not_construct)
    path = tmp_path / "model"
    if artifact_exists:
        path.write_text("not-a-model", encoding="utf-8")
    adapter = create_adapter(Settings(_env_file=None, model_artifact_path=path))
    assert adapter.mode == "real"
    assert adapter.state == ModelState.ERROR


def test_mock_factory_failure_stays_error(monkeypatch):
    from app.dev import mock_predictor

    def failing_factory():
        raise RuntimeError("test-only failure")

    monkeypatch.setattr(mock_predictor, "MockPredictor", failing_factory)
    adapter = create_adapter(Settings(_env_file=None, environment="test", predictor_mode="mock"))
    assert adapter.state == ModelState.ERROR
