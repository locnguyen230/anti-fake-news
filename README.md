# Anti-fake-news

Local FastAPI service with a multimodal model loader and an explicit dev/test mock.
Python **3.13** is the verified shared setup for Backend and ML on Windows x64.
See [ML environment](docs/ml-environment.md) for shared dependencies and CLIP checks.

Without a ready bundle, `GET /health` reports `model_ready: false` and `POST /predict`
returns HTTP 503 for valid requests. For synthetic responses during UI development,
enable the [dev/test mock](docs/dev-mock.md).

## Setup and run

Verified here: Windows x64, Python **3.13.1**. Reuse an existing working virtual environment.
This checkout uses `.venv/issue9`; this implementation creates no additional environment.
Old `.venv`/`.venv/verify` environments refer to an unavailable Python 3.10 installation.
They were preserved, not deleted. A fresh checkout may create one `.venv` with Python 3.13.1
and substitute its interpreter below. Linux/macOS and the complete ML environment are unverified.

From the repository root, PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
# Optional: copy only when you do not already have a local .env.
Copy-Item .env.example .env
# Supply AFN_DEMO_TOKEN privately in .env or this process environment.
cd backend
..\.venv\Scripts\python.exe -m app
```

On Linux/macOS (Python 3.13 installed):

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp -n .env.example .env
cd backend
../.venv/bin/python -m app
```

No activation needed; stop with Ctrl+C. The launcher honors AFN_HOST/AFN_PORT and accepts
only loopback hosts, default **127.0.0.1:8000**. Settings read root `.env`; process environment
wins. Health and docs: http://127.0.0.1:8000/health and http://127.0.0.1:8000/docs.
With the selected interpreter, equivalent explicit command from backend:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Explicit CLI bind options override settings. Keep this local service on loopback.

## Configuration

| Variable | Default / behavior |
| --- | --- |
| AFN_HOST | 127.0.0.1; loopback only |
| AFN_PORT | 8000; 1–65535 |
| AFN_ENVIRONMENT | demo; alternatives dev/test |
| AFN_PREDICTOR_MODE | real; mock requires dev/test |
| AFN_DEMO_TOKEN | Unset; every prediction gets 401 until configured, including mock |
| AFN_EXTENSION_ORIGIN | Unset; exact `chrome-extension://<32-char>` origin for CORS (see [local config](docs/local-config.md)) |
| AFN_MODEL_ARTIFACT_PATH | Multimodal bundle directory, relative to repo or absolute. Defaults to artifacts/model |
| AFN_MAX_REQUEST_BYTES | Enforced 12 MiB total body default; configurable above 10 MiB |

POST /predict requires X-Demo-Token, UUID, nonblank text (<=50,000 code points), optional
title (<=500), and one JPEG/PNG file (<=10 MiB, <=20 million pixels). Whole-body counting
includes multipart overhead and does not trust Content-Length. Invalid input is 400,
auth failure 401, byte overflow 413, validated input without a model 503. No 422 input errors.
GET /health is unauthenticated and does not imply real inference readiness.

Image validation uses the unchanged shared ML preprocessing helper from PR #68 for EXIF/RGB.
Pillow/NumPy are pinned to that ML manifest. Predictor retains original encoded bytes.
Do not log settings, credentials, articles/images, model exceptions or local artifact paths.

For real mode, install `backend/requirements.txt` and `ml/requirements.txt` into the same
environment, cache the pinned CLIP checkpoint and set `AFN_MODEL_ARTIFACT_PATH` to the
trusted local bundle directory. Startup validates the bundle, loads CLIP offline and warms up
the Predictor. See [bundle setup and lifecycle](docs/model-bundle.md).

## Verification

From the repository root, using the configured Python environment:

```sh
python -m pytest -q tests/test_model_loader.py backend/tests/test_inference_adapter.py
python scripts/test_extension_smoke.py
```

The browser smoke uses temporary loopback servers, an ephemeral token and synthetic inputs.
See [Extension smoke setup](docs/extension-w1.md) for Playwright and Chromium.

## Contracts and scope

- [API contract v0.2.0](docs/api-contract.md)
- [Predictor/shared preprocessing](docs/inference-interface.md)
- [Explicit mock usage and historical AFN-009 evidence](docs/dev-mock.md)
- [AFN-022/023 changes, tests and review handoff](docs/implementation-issues-22-23.md)
- [Historical AFN-007/008 evidence](docs/implementation-issues-7-8.md)
- Project context: [DEFINE.md](DEFINE.md), [DESIGN.md](DESIGN.md)

Candidate parity through the deployed Predictor and end-to-end QA remain in
#37–39. See the [week 2 checkpoint](reports/week-2-gate.md) for review status.
