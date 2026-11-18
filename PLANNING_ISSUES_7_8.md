# Agent Plan — GitHub Issues #7 and #8

**Repo:** `ngnsusinn/anti-fake-news`  
**Scope:** AFN-007 (#7, P0, 4h) and AFN-008 (#8, P0, 6h)  
**Week:** Nov 17–23, 2026 | **Owner:** Backend (`Phuc1232`)  
**Status:** Implementation plan, not proof of completion.

## 1. Mandatory instructions

Implement **only #7 and #8** in the current repo. First read `DEFINE.md` §§7–9, `DESIGN.md` §§2, 8–9, 12–14,README, and the latest issue descriptions if accessible. Inspect code, tests, dependency conventions and `git status --short`; preserve existing and uncommitted work. Record any conflicting requirements rather than silently altering them.

Do not modify ML training code, Extension code, research data, or model weights. Never commit secrets, actual tokens, raw data, checkpoints, or caches. Never claim tests/reviews/PRs exist without evidence. Implement, verify, and report blockers within this execution.

## 2. #7 — FastAPI foundation

**Required deliverables:** `backend/app/main.py`, `backend/requirements.txt`, `.env.example`, `.gitignore`, plus necessary config/test/run documentation.

Tasks:
- [ ] Create/adapt `backend/app/` and tests without duplicating existing code.
- [ ] Create a FastAPI entrypoint and startup/shutdown lifecycle; document a local run command binding **`127.0.0.1:8000`**, never public by default.
- [ ] Configure host/port, demo token, Chrome Extension origin, and model artifact path via environment variables; no real secret values in source or examples.
- [ ] Pin backend dependencies; check compatibility with ML dependencies and mark pending coordination if unconfirmed.
- [ ] Add a Predictor dependency-injection seam (provider/protocol/interface), **without implementing or loading the actual model**.
- [ ] Extend `.gitignore` safely: ignore `.env`, `.venv`, caches, raw/private data, weights/checkpoints/artifacts; keep `.env.example` trackable.
- [ ] Provide setup/run/test instructions that work on another machine.
- [ ] Ensure the app can start without model artifacts and never reports false model readiness.

**DoD:** reproducible install and startup, entrypoint/lifecycle/config/DI seam, safe env/gitignore, pinned dependencies, verification evidence and actual reviewer approval before marking Done.

## 3. #8 — API and inference contracts

**Required deliverables:** `docs/api-contract.md`, `docs/inference-interface.md`, `backend/app/schemas.py`.

### HTTP endpoints

| Method | Path | Meaning |
|---|---|---|
| GET | `/health` | Service/model readiness, without sensitive data |
| POST | `/predict` | Analyze an English article + one JPEG/PNG image using the selected multimodal model |

The Extension's `analyze.js` calls `/predict`; `service-worker.js` does not.

### POST /predict request

`Content-Type: multipart/form-data`, header `X-Demo-Token` required.

| Field | Required | Constraint |
|---|---|---|
| `request_id` | Yes | Valid UUID string |
| `title` | No | ≤500 characters |
| `text` | Yes | Nonempty after trim, ≤50,000 characters |
| `image` | Yes | JPEG/PNG, ≤10 MiB, ≤20 megapixels after decode |

The whole-request byte limit must be **larger than 10 MiB** to include text and multipart overhead; the project documents do not fix its exact value. Document any proposed value as configurable and pending agreement. A 50,000-character transport limit is distinct from the 1,500-word ML preprocessing limit. Image URL is not a substitute for uploaded image bytes. MIME headers/filename extensions alone do not validate an image (#23 covers actual decoding).

### Successful response (illustrative data only)

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "label": "real",
  "fake_score": 0.42,
  "model_version": "v1.0",
  "model_id": "multimodal-fake-news",
  "processing_time_ms": 250,
  "text_truncated": false
}
```

`label` must be `fake` or `real`; `fake_score` must be finite and in [0,1], and **is not a calibrated probability**. `processing_time_ms` is nonnegative and excludes model loading. `text_truncated` reflects downstream preprocessing. The numbers/IDs above are placeholders.

### Errors

Error JSON, illustrative:

```json
{
  "detail": "Invalid input",
  "error_code": "invalid_input",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| HTTP | error_code | Cause |
|---|---|---|
| 400 | `invalid_input` | Missing/malformed UUID, invalid/missing text, oversized title, bad image/MIME/pixels |
| 401 | `invalid_token` | Missing/invalid token |
| 403 | `forbidden` | Only when policy distinguishes authenticated-but-forbidden |
| 413 | `request_too_large` | Exceeded image or full-request byte limit |
| 503 | `model_not_ready` | Model/artifacts unavailable or incompatible |

Define `request_id` behavior for parsing errors (e.g., nullable when unavailable); **do not invent an ID**. FastAPI normally returns 422 for validation failures: document a strategy to map contract-covered errors to 400; implement a handler only where safely within this scope, and explicitly defer complete enforcement to #22/#23. No stack traces, local file paths, secrets, entire article or image bytes in logs/responses.

Client timeout is configurable; the ~10-second post-load inference goal is **not** a mandated timeout. A timed-out or stale client request does not guarantee server-side cancellation. CORS origin restrictions belong to #38 and do not replace token auth.

### Required implementation steps

- [ ] Write `docs/api-contract.md`: endpoint contract/version, multipart/header fields, constraints, total request overhead, sample cURL and JavaScript `FormData` requests, success/errors, 422 strategy, timeout, request correlation, security and readiness.
- [ ] Write `docs/inference-interface.md`: typed Predictor input/output; choice of raw bytes vs decoded image (flag for ML review); title/text flow; readiness/exceptions; model version/ID; lifecycle; ownership (ML owns model/preprocessing, Backend owns transport/validation); versioning and interface-change notification.
- [ ] Write `backend/app/schemas.py`: Pydantic response and error models, `fake|real` literal, finite score [0,1], nonnegative processing time, UUID and optional error request_id. Represent multipart fields appropriately; **do not treat uploaded files as JSON**.
- [ ] If defining endpoint skeletons, report model not-ready and never return synthetic successful predictions. Full auth, image validation and model loading are out of scope.
- [ ] Ensure all examples are labeled illustrative; request asynchronous ML and Extension review, but do not claim approval until actually obtained.

**DoD:** all three deliverables agree, constraints/error behavior documented, Predictor interface clear, no undocumented default 422 contradictions, review evidence before closing.

## 4. Execution phases and gates

### Phase A — Inspect
- [ ] Read design docs and issues; inspect repository, tests, README, dependency management, uncommitted edits.
- [ ] Document intended file changes and unresolved contract decisions.
**Gate:** existing work is preserved and scope is understood.

### Phase B — Implement #7
- [ ] Foundation, config/lifecycle, dependency pins, Predictor DI seam, safe env/gitignore, setup instructions, smoke test.
**Gate:** local app starts without ML model; no fake readiness or exposed credentials.

### Phase C — Implement #8
- [ ] API contract, inference contract, Pydantic schemas, consistent examples and optional safe skeletons.
- [ ] Notify ML/Extension of shared contracts and changes.
**Gate:** independent Backend/ML/Extension development is possible.

### Phase D — Test
- [ ] App imports and starts using documented localhost command.
- [ ] Env config works; no secrets tracked.
- [ ] Schemas reject invalid label, NaN/Infinity/out-of-range score, negative processing time.
- [ ] Docs cover all request fields, byte/pixel limits, 400/401/conditional 403/413/503 and 422 policy.
- [ ] Without model, no successful prediction or false ready state.
- [ ] `git diff --check` and relevant tests pass; record **actual** outputs.

Suggested commands (adapt to repository conventions):

```bash
python -m pip install -r backend/requirements.txt
cd backend
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify startup with a short-lived process or `TestClient`; stop any server afterward. Do not fabricate results.

### Phase E — Report
Provide changed files per issue, run instructions, executed tests/results, remaining blockers, unresolved ML/Extension decisions (Predictor signatures, dependency versions, total multipart limit, timeout, health schema, token policy), and DoD status (`done`/`partial`/`blocked`). Link commits/PRs only if created. Do not close issues without authorization.

## 5. Explicit exclusions

Do **not** implement the following prematurely:

| Issue | Deferred responsibility |
|---|---|
| #9 | Full mock Predictor, readiness lifecycle |
| #22 | Complete token validation and streaming/request-size enforcement |
| #23 | Full image content verification, decode, EXIF/RGB |
| #37 | Real TF-IDF + CLIP + Logistic Regression inference |
| #38 | Complete CORS, warm-up, readiness and local hardening |
| #39 | Model integration testing |

Do not introduce DB, Redis, Docker, cloud, external AI API or CI/CD unless independently required by the repo. Skeletons needed for #7/#8 are fine if documented as incomplete.

## 6. Agent prompt

> Read `PLANNING_ISSUES_7_8_EN.md`, `DEFINE.md`, `DESIGN.md`. Inspect existing code and uncommitted changes first. Execute Phases A–E to implement **only** #7 (AFN-007) and #8 (AFN-008). Build a runnable local FastAPI foundation, safe configuration, pinned dependencies, Predictor DI seam, API/inference contract docs, typed Pydantic schemas and appropriate tests. Preserve other work, do not fabricate predictions or test/review results, and do not implement deferred issues. Report actual file changes, commands/results, blockers and ML/Extension review status. Do not close GitHub issues without authorization.

## References

- [Issue #7](https://github.com/ngnsusinn/anti-fake-news/issues/7)
- [Issue #8](https://github.com/ngnsusinn/anti-fake-news/issues/8)
- `DEFINE.md` §§7–9; `DESIGN.md` §§2, 8–9, 12–14; 
