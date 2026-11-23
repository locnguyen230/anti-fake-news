# QA test plan — AFN-014 (draft, 2026-11-23)

Target: Chromium extension → local FastAPI → real Predictor. All cases below are **planned**, not recorded passes. Traceability uses F01–F08 from `DEFINE.md` (issue's `FR-01`…`FR-08` aliases). Current `DESIGN.md` does not define T01–T12; this table assigns stable QA case IDs pending team confirmation. NFR: extraction ≥8/10 selected article pages and median inference <10s across ≥20 real runs on the demo CPU, measured at final acceptance, not with mock.

| Case | FR / NFR | Implementation owner/issue | Steps / input | Expected result | Evidence to retain |
| --- | --- | --- | --- | --- | --- |
| T01 | F01 | EXTENSION #10 | Click extension on selected article, then another tab | Session retains correct tab ID/source URL; no cross-tab leakage | tab/session log without article content, screenshot |
| T02 | F02 | EXTENSION #11 | Load ordinary article, empty/dynamic DOM, relative image URL | Extract title/body, correct absolute candidate URL; fallback permits manual text | sanitized extraction comparison against 10-page checklist |
| T03 | F03 | EXTENSION #25 | Choose one of several image candidates or upload permitted local PNG | Preview and selected file match; only one image is submitted | screenshot, request metadata |
| T04 | F04 | EXTENSION #26 / BACKEND #22–23 | Submit empty/whitespace text; then >50,000 codepoints or title >500 | Input rejected without prediction, user input retained | UI screenshot, sanitized 400 error |
| T05 | F04 | BACKEND #22–23 | Upload corrupt bytes, wrong declared MIME, oversized >10 MiB, EXIF-oriented JPEG | Corrupt/wrong MIME rejected on validated real path; 413 for size; orientation handled as approved | status/error code, decoder verification |
| T06 | F05 | EXTENSION #27 / BACKEND #22 | Inspect requests before and after explicit Analyze click | No POST before click; multipart fields `request_id`, optional `title`, `text`, `image` match agreed contract; no JSON image | network capture redacted |
| T07 | F06 | BACKEND #37 / EXTENSION #40 | Real model ready; analyze a permitted text+image fixture | `fake|real`, finite `fake_score` 0..1, real model/version ID, nonnegative latency shown with disclaimer | actual response redacted, model artifact hash |
| T08 | F07 | EXTENSION #41 / BACKEND #38 | Stop API; retry; induce timeout/network failure and CORS rejection | Clear recoverable error, inputs retained, no fabricated result or unsafe retry | screenshots, statuses, server state |
| T09 | F07 | EXTENSION #42 | Start request A then B in same tab; return A after B | Stale A response ignored, B owns displayed result; other tabs unaffected | timestamped request IDs (synthetic) |
| T10 | F08 | DATA #18 / ML #34 | Audit manifest, group keys, 70/15/15 split, fixed seed and training scripts | No group leakage; all models use same split; Test unseen during selection | manifest/split checksums, audit log |
| T11 | F08 | ML #34 / #49–50 | Validate three predeclared model configurations using only Train/Validation | C and threshold chosen on Validation; Test opened only after freeze; Macro-F1 and per-class metrics retained | config hash, frozen run log, aggregate metrics |
| T12 | NFR + F01–F08 | QA #43 / INTEGRATION #45 / BACKEND #52 | End-to-end on selected 10 article pages, ≥20 measured real calls on demo machine | Record actual extraction pass rate, median real inference latency, machine info, errors; compare to DEFINE goals without substituting mock | page checklist and timing CSV, version hashes |

## Fixture namespaces and method

- QA-owned synthetic fixtures: `tests/fixtures/qa/v0.1.1/`, described in [fixture manifest](../tests/fixtures/README.md). Never put third-party articles/images in version control without rights.
- Backend-owned contract fixtures already in `backend/tests/fixtures/api/v0.1.1/`; keep them as **development examples**, not independent scientific Test or evidence of a real model.
- Research split: `Train` fits vectorizers/classifier; `Validation` selects hyperparameters/threshold; `Test` stays sealed until freeze and is never consumed for UI debugging, model selection, benchmarking, demos or retry-based tuning. QA may audit Test **metadata only** (counts, hashes, split/group overlap) before lock, not labels/predictions/content for tuning.
- For race/timeout/CORS, record environment (browser version, localhost origin, extension ID redacted), exact steps, request UUIDs, status and expected/actual separately. A browser abort need not cancel server work. CORS is not authentication; token enforcement is a separate check.

## Contract boundary and blockers

Current contract [v0.1.1](api-contract.md) is proposed and pending Backend/ML/Extension sign-off (#8); full auth/limits/decoding/CORS/real inference are deferred to #22/#23/#38/#37. Do not mark T04–T08 passed because of mock-only behavior. DEFINE specifies Vietnamese but proposed interface flags an English-input conflict; await approved decision. T10–T12 depend on group split, CLIP CPU smoke and real model. Track all runs in a table with `case | build SHA | fixture version | environment | expected | actual | PASS/FAIL/BLOCKED | evidence URL | tester | date`.

Acceptance handoff: QA `dangnguyen0512`; DATA role reviewer `locnguyen230`; mandatory codeowner `ngnsusinn`. Test-case naming and matrix are ready for review, not a Test result.
