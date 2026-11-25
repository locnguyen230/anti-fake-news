"""AFN-028: kiểm thử hợp đồng API v0.2.0 độc lập với mô hình nghiên cứu.

Chạy: python -m unittest discover -s tests -p test_api_contract.py -v
Chế độ mock được bật tường minh và không đại diện cho suy luận thật.
"""

from io import BytesIO
from pathlib import Path
import sys
import unittest
from uuid import UUID

from PIL import Image
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


TOKEN = "qa-only-synthetic-token"
REQUEST_ID = "550e8400-e29b-41d4-a716-446655440000"


def make_image(format="PNG", size=(2, 2), orientation=None):
    with Image.new("RGB", size, (30, 120, 210)) as image, BytesIO() as stream:
        kwargs = {}
        if orientation is not None:
            exif = Image.Exif()
            exif[274] = orientation
            kwargs["exif"] = exif
        image.save(stream, format=format, **kwargs)
        return stream.getvalue()


def app(mode="mock", with_token=True):
    return create_app(Settings(
        _env_file=None, environment="test", predictor_mode=mode,
        demo_token=TOKEN if with_token else None,
    ))


def post(client, *, data=None, image=None, mime="image/png", headers=None):
    if data is None:
        data = {"request_id": REQUEST_ID, "title": "Synthetic title", "text": "Synthetic article"}
    if image is None:
        image = make_image()
    return client.post("/predict", data=data,
                       files={"image": ("fixture.png", image, mime)},
                       headers={"X-Demo-Token": TOKEN} if headers is None else headers)


class ApiContractQATests(unittest.TestCase):
    def assert_error(self, response, status, code, request_id=None):
        self.assertEqual(response.status_code, status, response.text)
        payload = response.json()
        self.assertEqual(set(payload), {"detail", "error_code", "request_id"})
        self.assertEqual(payload["error_code"], code)
        self.assertEqual(payload["request_id"], request_id)
        self.assertNotIn("Synthetic article", response.text)
        self.assertNotIn(TOKEN, response.text)

    def test_health_does_not_claim_real_model_ready(self):
        with TestClient(app("real")) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["contract_version"], "0.2.0")
            self.assertFalse(response.json()["model_ready"])
            self.assertEqual(response.headers["X-AFN-Inference-Mode"], "real")
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_explicit_mock_success_is_identifiable(self):
        with TestClient(app()) as client:
            response = post(client)
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(str(UUID(payload["request_id"])), REQUEST_ID)
            self.assertIn(payload["label"], ("fake", "real"))
            self.assertTrue(0 <= payload["fake_score"] <= 1)
            self.assertGreaterEqual(payload["processing_time_ms"], 0)
            self.assertIs(type(payload["text_truncated"]), bool)
            self.assertEqual(payload["model_id"], "dev-mock-not-a-model")
            self.assertEqual(response.headers["X-AFN-Inference-Mode"], "mock")

    def test_valid_input_real_mode_stays_503(self):
        with TestClient(app("real")) as client:
            self.assert_error(post(client), 503, "model_not_ready", REQUEST_ID)

    def test_auth_precedes_bad_body_in_both_modes(self):
        for mode in ("real", "mock"):
            with self.subTest(mode=mode), TestClient(app(mode)) as client:
                for headers in ({}, {"X-Demo-Token": "wrong"}):
                    response = client.post("/predict", content=b"not multipart", headers=headers)
                    self.assert_error(response, 401, "invalid_token")

    def test_unconfigured_server_token_fails_closed(self):
        with TestClient(app(with_token=False)) as client:
            self.assert_error(post(client), 401, "invalid_token")

    def test_required_fields_and_uuid(self):
        for removed in ("request_id", "text"):
            with self.subTest(removed=removed), TestClient(app()) as client:
                data = {"request_id": REQUEST_ID, "text": "test"}
                del data[removed]
                response = post(client, data=data)
                expected_id = REQUEST_ID if removed == "text" else None
                self.assert_error(response, 400, "invalid_input", expected_id)
        with TestClient(app()) as client:
            self.assert_error(post(client, data={"request_id": "bad", "text": "test"}),
                              400, "invalid_input")

    def test_text_and_title_boundaries(self):
        for name, text, expected in [
            ("blank body", " \n ", 400),
            ("text 50000", "a" * 50_000, 200),
            ("text 50001", "a" * 50_001, 400),
        ]:
            with self.subTest(name=name), TestClient(app()) as client:
                result = post(client, data={"request_id": REQUEST_ID, "text": text})
                self.assertEqual(result.status_code, expected, result.text)
        for count, expected in ((500, 200), (501, 400)):
            with self.subTest(title_size=count), TestClient(app()) as client:
                response = post(client, data={"request_id": REQUEST_ID, "text": "test",
                                              "title": "x" * count})
                self.assertEqual(response.status_code, expected, response.text)

    def test_malformed_multipart_is_400_not_422(self):
        with TestClient(app()) as client:
            for kwargs in ({"json": {"request_id": REQUEST_ID, "text": "test"},
                            "headers": {"X-Demo-Token": TOKEN}},
                           {"content": b"corrupt", "headers": {
                               "X-Demo-Token": TOKEN, "Content-Type": "multipart/form-data"}}):
                with self.subTest(kwargs=tuple(kwargs)):
                    response = client.post("/predict", **kwargs)
                    self.assert_error(response, 400, "invalid_input")

    def test_duplicate_or_unknown_parts(self):
        valid = [("request_id", (None, REQUEST_ID)), ("text", (None, "test")),
                 ("image", ("a.png", make_image(), "image/png"))]
        for extra in (("text", (None, "again")), ("unknown", (None, "x"))):
            with self.subTest(extra=extra[0]), TestClient(app()) as client:
                response = client.post("/predict", files=valid + [extra],
                                       headers={"X-Demo-Token": TOKEN})
                self.assert_error(response, 400, "invalid_input", REQUEST_ID)

    def test_missing_image_corrupt_bytes_and_mime_mismatch(self):
        with TestClient(app()) as client:
            missing = client.post("/predict", files={"request_id": (None, REQUEST_ID),
                                                     "text": (None, "test")},
                                  headers={"X-Demo-Token": TOKEN})
            self.assert_error(missing, 400, "invalid_input", REQUEST_ID)
            for raw, mime in ((b"broken image", "image/png"),
                              (make_image(), "image/jpeg"),
                              (make_image(), "text/plain")):
                with self.subTest(mime=mime, bytes=len(raw)):
                    self.assert_error(post(client, image=raw, mime=mime),
                                      400, "invalid_input", REQUEST_ID)

    def test_image_byte_limit_is_413(self):
        with TestClient(app()) as client:
            response = post(client, image=b"x" * (10 * 1024 * 1024 + 1))
            self.assert_error(response, 413, "request_too_large")

    def test_valid_exif_image_is_accepted_as_mock_only(self):
        jpeg = make_image("JPEG", (3, 2), orientation=6)
        with TestClient(app()) as client:
            response = post(client, image=jpeg, mime="image/jpeg")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["model_id"], "dev-mock-not-a-model")

    def test_no_403_policy_is_not_misreported(self):
        with TestClient(app()) as client:
            self.assert_error(post(client, headers={"X-Demo-Token": "wrong"}),
                              401, "invalid_token")


if __name__ == "__main__":
    unittest.main()
