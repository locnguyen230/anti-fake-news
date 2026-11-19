# API fixtures v0.1.1

All bodies are **synthetic development examples**, not model results or measured
performance. `manifest.json` declares each HTTP status, headers, body filename and
Pydantic schema. Import the JSON into Extension unit/UI tests without running a
real model. Keep an obvious mock indicator in the UI.

- `predict-mock.json`: fixed model fields from MockPredictor. The request UUID is
  illustrative; a running API echoes the submitted UUID. Timing `0` is a fixture
  placeholder; the endpoint measures actual call time. Never use this fixture
  to report model accuracy or inference latency.
- `health-real-not-loaded.json`: default real mode, unavailable.
- `health-mock-ready.json`: mock provider ready, not a trained model.
- `not-ready.json`: pre-parse 503; no UUID available.
- `not-ready-correlated.json`: mock provider failure after parsing; UUID retained.
- `invalid-input*.json`: mock input 400 with nullable or parsed UUID.
- `request-too-large.json`: mock post-parse image-copy guard 413.

No 401/403 or complete request-limit fixtures are claimed as implemented by #9;
these remain #22. Headers distinguish mode/state without adding JSON fields.
Changing fields/semantics requires coordinated docs/schemas/fixtures and consumer
review. This is the repository's existing `backend/tests` layout, rather than a
second top-level test tree.
