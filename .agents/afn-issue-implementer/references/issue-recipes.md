# Known issue recipes — examples, not timeless specifications

Always fetch the live GitHub issue, its links and comments before implementation. These are guideposts for triage.

| Issue | Core work | Known dependencies / boundaries |
|---|---|---|
| #7 / AFN-007 | Local FastAPI foundation, config, entrypoint, pinned dependencies, Predictor DI seam, safe `.env.example` / `.gitignore` | ML compatibility/review; not real model loading |
| #8 / AFN-008 | HTTP API contract, Pydantic schemas, Predictor interface and error semantics | ML + Extension review; don't silently change 422/error behavior |
| #9 / AFN-009 | `GET /health` state, explicitly opt-in dev/test mock Predictor, inference adapter, versioned API fixtures, `docs/dev-mock.md` | #8 to start; #7+#8 for Done; no real-model fallback to mock; real mode without artifacts returns 503 |
| #22 / AFN-022 | Token authentication, request/multipart limits | Use current contracts; don't confuse request total size with image size |
| #23 / AFN-023 | Image MIME/bytes/decode/pixel validation and ML preprocessing boundary | Coordinate with ML-owned preprocessing; don't edit ML source unnecessarily |
| #37 / AFN-037 | Real multimodal inference integration | Requires model artifacts and compatibility checks; no mock output in demo |
| #38 / AFN-038 | CORS, readiness, local runtime/warm-up | CORS is browser policy, not a substitute for token auth |
| #39 / AFN-039 | End-to-end Backend and real-model integration tests | Use actual model and permissible fixtures, not mock-only acceptance |
| #52 / AFN-052 | Local demo performance and resource measurements | Separate model loading from request processing; report measured values only |
| #53 / AFN-053 | Regression fixes and release blocking issues | Respect frozen model/threshold and record verification |

## #9 specific checklist

1. Inspect existing `backend/app/inference_adapter.py`, `backend/app/main.py`, `backend/app/schemas.py`, contract docs, and tests; avoid duplicating interfaces.
2. Implement or extend Predictor readiness (`not_loaded`, `ready`, `error`) with consistent public health schema.
3. Implement `backend/app/dev/mock_predictor.py` respecting the approved Predictor protocol.
4. Enable mock **only** through explicit dev/test configuration; default real mode must not fall back to mock when actual model load fails.
5. Provide versioned response/error fixtures under `tests/fixtures/api/` (or repo's adopted tests path) and `docs/dev-mock.md` with precise usage instructions.
6. Verify `GET /health` discloses no secrets, mode without artifacts never claims real readiness, and real-mode `/predict` returns 503 when not ready.
7. Don't expand into full token enforcement (#22), image processing (#23), real inference (#37), full CORS/warm-up (#38), or ML integration testing (#39), unless specifically assigned.

## Acceptance evidence template

| Criterion | State | Verification | Remaining action |
|---|---|---|---|
| [Exact wording from live issue] | PASS/PARTIAL/BLOCKED/NOT RUN | [test command, output, file:line or PR] | [if any] |

## Short invocations

- `Use afn-issue-implementer to implement #9 in ngnsusinn/anti-fake-news. Fetch the live issue and repo, follow dependencies, run tests, and report evidence. Don't close it.`
- `Use afn-issue-implementer to plan AFN-037 without changing code.`
- `Use afn-issue-implementer to implement #22 and #23, resolving dependencies and keeping ML-owned modules unchanged.`
