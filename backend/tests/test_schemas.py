from uuid import UUID

import pytest
from pydantic import ValidationError

from app.predictor import PredictorInput
from app.schemas import ErrorResponse, HealthResponse, PredictFormFields, PredictResponse

REQUEST_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def illustrative_result():
    # Schema fixture only: this is not a model prediction or evaluation result.
    return dict(request_id=REQUEST_ID, label="real", fake_score=0.42,
                model_version="test-only", model_id="test-only",
                processing_time_ms=0, text_truncated=False)


@pytest.mark.parametrize("score", [0, 1, 0.42])
def test_response_round_trip(illustrative_result, score):
    result = PredictResponse(**(illustrative_result | {"fake_score": score}))
    assert result.request_id == UUID(REQUEST_ID)
    assert PredictResponse.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("field,value", [
    ("label", "unknown"), ("label", "FAKE"),
    ("fake_score", float("nan")), ("fake_score", float("inf")),
    ("fake_score", -float("inf")), ("fake_score", -0.01), ("fake_score", 1.01),
    ("fake_score", "0.5"), ("fake_score", True),
    ("processing_time_ms", -1), ("processing_time_ms", 1.5),
    ("processing_time_ms", float("inf")), ("processing_time_ms", True),
    ("text_truncated", "false"), ("request_id", "not-a-uuid"),
    ("model_version", ""), ("model_id", "   "),
])
def test_response_rejects_invalid_values(illustrative_result, field, value):
    with pytest.raises(ValidationError):
        PredictResponse(**(illustrative_result | {field: value}))


def test_form_limits_and_trim():
    fields = PredictFormFields(request_id=REQUEST_ID, title="t" * 500, text="🙂" * 50_000)
    assert len(fields.text) == 50_000
    assert PredictFormFields(request_id=REQUEST_ID, text="  body\n").text == "body"
    assert PredictFormFields(request_id=REQUEST_ID, text="body").title is None


@pytest.mark.parametrize("overrides", [
    {"request_id": "bad"}, {"title": "t" * 501}, {"text": ""},
    {"text": " \n\t "}, {"text": "x" * 50_001},
    {"text": " " * 50_000 + "x"}, {"text": None}, {"text": 123},
    {"image": "https://example.com/image.png"},
])
def test_form_rejects_invalid_fields(overrides):
    with pytest.raises(ValidationError):
        PredictFormFields(**(dict(request_id=REQUEST_ID, text="body") | overrides))


@pytest.mark.parametrize("missing", ["request_id", "text"])
def test_form_requires_id_and_text(missing):
    fields = dict(request_id=REQUEST_ID, text="body")
    del fields[missing]
    with pytest.raises(ValidationError):
        PredictFormFields(**fields)


def test_error_correlation_is_nullable_but_not_fabricated():
    error = ErrorResponse(detail="Model is not ready", error_code="model_not_ready")
    assert error.model_dump(mode="json")["request_id"] is None
    correlated = ErrorResponse(detail="Invalid input", error_code="invalid_input", request_id=REQUEST_ID)
    assert correlated.model_dump(mode="json")["request_id"] == REQUEST_ID
    with pytest.raises(ValidationError):
        ErrorResponse(detail="Invalid input", error_code="invalid_input", request_id="bad")


def test_inference_input_requires_bytes_separate_from_form():
    fields = dict(request_id=REQUEST_ID, text="body")
    for value in (b"", "https://example.com/image.png"):
        with pytest.raises(ValidationError):
            PredictorInput(**fields, image_bytes=value)
    # Typing only; bytes are deliberately not claimed to be a verified image.
    inputs = PredictorInput(**fields, image_bytes=b"typing-fixture")
    assert "typing-fixture" not in repr(inputs)
    assert "image" not in PredictFormFields.model_fields


def test_health_does_not_accept_truthy_strings():
    with pytest.raises(ValidationError):
        HealthResponse(model_ready="false")
