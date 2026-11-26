"""Load and warm up one trusted multimodal bundle for Backend inference."""

import json
from io import BytesIO
from uuid import UUID

from PIL import Image
from jsonschema import Draft202012Validator

from app.clip_encoder import ClipImageEncoder
from app.config import REPO_ROOT, Settings
from app.model_bundle import BundleError, check_encoder_identity, load_bundle
from app.predictor import BundlePredictor, PredictorInput


METADATA_SCHEMA = REPO_ROOT / "backend" / "artifacts" / "metadata.schema.json"


def load_predictor(settings: Settings) -> BundlePredictor:
    bundle = load_bundle(
        settings.model_artifact_path,
        expected_configuration="multimodal",
        expected_metadata_sha256=settings.model_metadata_sha256,
    )
    schema = json.loads(METADATA_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    if not validator.is_valid(bundle.metadata):
        raise BundleError("bundle metadata does not match the schema")
    is_fixture = bundle.metadata["is_fixture"]
    if any(value.endswith("-fixture") != is_fixture for value in (bundle.model_id, bundle.model_version)):
        raise BundleError("bundle identifiers disagree with fixture metadata")
    if is_fixture and settings.environment not in ("dev", "test"):
        raise BundleError("a fixture bundle requires dev or test")
    if settings.environment == "production" and bundle.metadata["status"] != "frozen":
        raise BundleError("production requires a frozen bundle")

    encoder = ClipImageEncoder(offline=True)
    check_encoder_identity(bundle, encoder.identity, encoder.dim)
    predictor = BundlePredictor(bundle, encoder)
    with Image.new("RGB", (32, 32), (80, 120, 180)) as image, BytesIO() as stream:
        image.save(stream, format="PNG")
        predictor.predict(
            PredictorInput(request_id=UUID(int=0), text="Synthetic startup check", image_bytes=stream.getvalue())
        )
    return predictor
