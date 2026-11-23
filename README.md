# Anti-fake-news

Local FastAPI foundation, explicit dev/test mock, authenticated request limits and image
validation (AFN-007/008/009/022/023). Contract **v0.2.0**; ML/Extension review pending.
Real mode has no model loader: valid authenticated requests return 503. Mock responses are
synthetic and clearly marked `dev-mock-not-a-model`, never evidence of ML accuracy.

## Setup and run

Verified here: Windows x64, Python **3.13.1**. Reuse an existing working virtual environment.
This checkout uses `.venv/issue9`; this implementation creates no additional environment.
Old `.venv`/`.venv/verify` environments refer to an unavailable Python 3.10 installation.
They were preserved, not deleted. A fresh checkout may create one `.venv` with Python 3.13.1
and substitute its interpreter below. Linux/macOS and the complete ML environment are unverified.

From the repository root, PowerShell:

```powershell
.\.venv\issue9\Scripts\python.exe -m pip install -r backend/requirements.txt
# Optional: copy only if you have no local .env yet.
Copy-Item .env.example .env
# Supply AFN_DEMO_TOKEN privately in .env or this process environment.
cd backend
..\.venv\issue9\Scripts\python.exe -m app
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
| AFN_EXTENSION_ORIGIN | Unset; enforcement remains #38 |
| AFN_MODEL_ARTIFACT_PATH | artifacts/model relative to repo; no loader yet |
| AFN_MAX_REQUEST_BYTES | Enforced 12 MiB total body default; configurable above 10 MiB |

POST /predict requires X-Demo-Token, UUID, nonblank text (<=50,000 code points), optional
title (<=500), and one JPEG/PNG file (<=10 MiB, <=20 million pixels). Whole-body counting
includes multipart overhead and does not trust Content-Length. Invalid input is 400,
auth failure 401, byte overflow 413, validated input without a model 503. No 422 input errors.
GET /health is unauthenticated and does not imply real inference readiness.

Image validation uses the unchanged shared ML preprocessing helper from PR #68 for EXIF/RGB.
Pillow/NumPy are pinned to that ML manifest. Predictor retains original encoded bytes.
Do not log settings, credentials, articles/images, model exceptions or local artifact paths.

## Verification

From backend, using the same environment:

```powershell
..\.venv\issue9\Scripts\python.exe -m pytest -q
..\.venv\issue9\Scripts\python.exe -m pip check
..\.venv\issue9\Scripts\python.exe tests/smoke_local.py
..\.venv\issue9\Scripts\python.exe tests/smoke_local.py --mode mock
```

Run smoke commands sequentially; each reserves port 8000, creates an ephemeral token and
synthetic PNG, and stops its own server. They do not test trained-model accuracy.
Requirements pin runtime, image helper and test dependencies; no configured lint/type checker.

## Contracts and scope

- [API contract v0.2.0](docs/api-contract.md)
- [Predictor/shared preprocessing](docs/inference-interface.md)
- [Explicit mock usage and historical AFN-009 evidence](docs/dev-mock.md)
- [AFN-022/023 changes, tests and review handoff](docs/implementation-issues-22-23.md)
- [Historical AFN-007/008 evidence](docs/implementation-issues-7-8.md)
- Project context: [DEFINE.md](DEFINE.md), [DESIGN.md](DESIGN.md)

#37 model loading, #38 CORS/warm-up and #39 integration remain deferred; #28 QA-owned work
is untouched. Real ML inference and browser cross-origin integration are not implemented here.
Code verification does not replace ML/Extension review or authorize closing GitHub issues.
