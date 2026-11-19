"""Fixed synthetic result for UI development, never model-quality evidence."""

from app.predictor import PredictorInput
from app.schemas import PredictionResult

MOCK_MODEL_ID = "dev-mock-not-a-model"
MOCK_MODEL_VERSION = "mock-v0.1.1"


class MockPredictor:
    def predict(self, inputs: PredictorInput) -> PredictionResult:
        # Deliberately independent of content: no model, language detection,
        # thresholding, image verification or preprocessing occurs here.
        return PredictionResult(
            label="real", fake_score=0.42, model_id=MOCK_MODEL_ID,
            model_version=MOCK_MODEL_VERSION, text_truncated=False,
        )
