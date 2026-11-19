# Anti-fake-news

Local FastAPI foundation and dev mock for **AFN-007 / AFN-008 / AFN-009**. Python **3.10** is the
initial dependency baseline (tested patch version is recorded in the execution
report). ML environment compatibility and reviewer approval remain pending.

By default, `GET /health` reports `model_ready: false` and `POST /predict`
returns HTTP 503 without reading uploads. An explicit dev/test mock can return
synthetic responses for UI development; see [dev-mock.md](docs/dev-mock.md).
This is not a real-model demo. The current verification used Python 3.13.1;
ML environment agreement is still pending.

## Setup and run

From the repository root, on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
# Optional: copy only when you do not already have a local .env.
Copy-Item .env.example .env
cd backend
..\.venv\Scripts\python.exe -m app
```

On Linux/macOS (Python 3.10 installed):

```sh
python3.10 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp -n .env.example .env
cd backend
../.venv/bin/python -m app
```

No environment activation is required. Stop the server with Ctrl+C.
The launcher defaults to **127.0.0.1:8000**. It honors `AFN_HOST` and `AFN_PORT`;
only loopback hosts are accepted. Settings read `.env` at the repository root
regardless of working directory. Process environment overrides `.env`.

Equivalent explicit Uvicorn command, from `backend` with the virtual environment
Python selected:

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The explicit CLI host/port above override bind selection; use `python -m app`
to honor `AFN_HOST` / `AFN_PORT`. Do not bind this unfinished skeleton publicly.
Visit <http://127.0.0.1:8000/health> or <http://127.0.0.1:8000/docs>.
OpenAPI describes **current** behavior; the target multipart API is specified
in [the contract](docs/api-contract.md).

## Configuration

| Environment variable | Default / meaning |
| --- | --- |
| `AFN_HOST` | `127.0.0.1`; loopback only |
| `AFN_PORT` | `8000`; 1–65535 |
| `AFN_ENVIRONMENT` | `demo`; alternatives `dev`, `test` |
| `AFN_PREDICTOR_MODE` | `real`; `mock` is accepted only in dev/test |
| `AFN_DEMO_TOKEN` | Unset; secret stored with `SecretStr`, auth deferred to #22 |
| `AFN_EXTENSION_ORIGIN` | Unset; one `chrome-extension://` origin, enforcement deferred to #38 |
| `AFN_MODEL_ARTIFACT_PATH` | `<repo>/artifacts/model`; relative values resolve from repo root |
| `AFN_MAX_REQUEST_BYTES` | Proposed 12 MiB (12,582,912 bytes), must exceed 10 MiB; enforcement deferred to #22 |

An empty token/origin is unconfigured, never an authentication bypass for a
real prediction endpoint. The explicitly opted-in mock does not enforce tokens;
use synthetic test content only. No token is generated, printed or committed here.
No model files are read, even if an artifact path exists. Do not log settings,
request bodies, credentials, model exceptions or file paths.

## Tests

From repository root, Windows:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
# Optional: real HTTP smoke on port 8000; stops its own server afterward.
..\.venv\Scripts\python.exe tests/smoke_local.py
..\.venv\Scripts\python.exe tests/smoke_local.py --mode mock
```

On Linux/macOS, use `../.venv/bin/python` in these commands. The requirement
file pins runtime **and test** dependencies, including the resolved transitive
packages. It intentionally contains no ML packages. Tests cover startup/shutdown,
environment configuration, no-model behavior, dependency overrides and schema
boundaries, adapter state and synthetic mock responses. They do not evaluate a trained model.

## Contracts and remaining work

- [HTTP contract v0.1.1](docs/api-contract.md)
- [Predictor interface v0.1.1](docs/inference-interface.md)
- [Explicit dev/test mock and AFN-009 evidence](docs/dev-mock.md)
- [Execution evidence and review handoff](docs/implementation-issues-7-8.md)
- Existing project context: [DEFINE.md](DEFINE.md), [DESIGN.md](DESIGN.md)

Full implementation of #22, #23, #37, #38 and #39 remains deferred. In particular,
full authentication, streaming request limits, image decoding, CORS, model loading,
warm-up and integration tests remain deferred. The target contract is a proposal
until Backend, ML and Extension approve it.
