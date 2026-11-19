"""Minimal mock-only multipart bridge; not the #22/#23 production validator."""

from typing import Literal
from uuid import UUID

from fastapi import Request
from pydantic import ValidationError
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

from app.config import IMAGE_MAX_BYTES
from app.predictor import PredictorInput
from app.schemas import PredictFormFields


class MockInputError(Exception):
    def __init__(self, request_id: UUID | None = None, *, too_large: bool = False) -> None:
        self.request_id = request_id
        self.status_code = 413 if too_large else 400
        self.error_code: Literal["invalid_input", "request_too_large"] = (
            "request_too_large" if too_large else "invalid_input"
        )
        self.detail = "Request is too large" if too_large else "Invalid input"


async def read_mock_input(request: Request) -> PredictorInput:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
        raise MockInputError
    request_id = None
    try:
        # Use the framework's parser bounds. Whole-request streaming enforcement
        # is still #22; these limits do not cap uploaded file bytes during parse.
        async with request.form(max_files=1, max_fields=3, max_part_size=200_000) as form:
            ids = form.getlist("request_id")
            if len(ids) == 1 and isinstance(ids[0], str):
                try:
                    request_id = UUID(ids[0])
                except ValueError:
                    pass
            allowed = {"request_id", "title", "text", "image"}
            if set(form) - allowed or any(len(form.getlist(key)) > 1 for key in allowed):
                raise MockInputError(request_id)
            fields = PredictFormFields.model_validate({
                "request_id": form.get("request_id"),
                "title": form.get("title"), "text": form.get("text"),
            })
            image = form.get("image")
            if not isinstance(image, UploadFile):
                raise MockInputError(request_id)
            # Bounded copy after parsing, not streamed request-limit enforcement.
            image_bytes = await image.read(IMAGE_MAX_BYTES + 1)
            if len(image_bytes) > IMAGE_MAX_BYTES:
                raise MockInputError(request_id, too_large=True)
            return PredictorInput(**fields.model_dump(), image_bytes=image_bytes)
    except (ValidationError, MultipartParseError):
        raise MockInputError(request_id) from None
    except HTTPException as exc:
        if exc.status_code != 400:
            raise
        raise MockInputError(request_id) from None
