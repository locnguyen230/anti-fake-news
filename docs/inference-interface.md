# Predictor interface v0.1.0 — AFN-007 / AFN-008

Status: **proposed**, ML and Extension review pending. No model or complete mock
Predictor is implemented. `backend/app/predictor.py` is the typed DI seam;
`backend/app/schemas.py` defines shared input/result constraints.

## Proposed Python boundary

```python
class PredictorInput(PredictFormFields):
    image_bytes: bytes

class Predictor(Protocol):
    def predict(self, inputs: PredictorInput) -> PredictionResult: ...
```

`PredictFormFields` contains `request_id: UUID`, `title: str | None` (<=500 code
points) and `text: str` (<=50,000 code points before trim, nonblank after trim).
An HTTP upload is a separate multipart file part; it is never a JSON byte string
or image URL. Backend eventually validates the transport, then constructs
`PredictorInput`. The bytes field requires nonempty `bytes`, but its schema alone
does **not** verify MIME, byte/pixel ceilings or decodability.

**Proposed image choice: validated encoded JPEG/PNG bytes.** This avoids a Pillow,
NumPy, Torch or CLIP dependency in the foundation. Backend #23 must verify contents,
dimensions (<=20,000,000 pixels), <=10 MiB size, and define EXIF/RGB handling.
ML owns model-specific image transforms. Passing validated encoded bytes may
require ML to decode again; ML must review whether to replace this boundary with
a decoded RGB object. Exact decode/orientation/normalization ownership must be
agreed before #23/#37. Changing it requires a versioned interface update, not an
undocumented switch. No decode is implemented here.

Pass optional title and trimmed body separately. Backend only validates transport
length/blankness; it does not concatenate or truncate. ML owns consistent
training/inference concatenation, tokenization, the proposed 1,500-word ceiling
and how title words count. ML sets `text_truncated` when preprocessing truncates.
The English input scope and exact preprocessing are pending ML approval.
Do not use request_id, URLs, filenames or other provenance as model features.

## Output and failures

`PredictionResult` contains:

| Field | Type / responsibility |
| --- | --- |
| `label` | Literal `fake` or `real`, ML threshold and class mapping |
| `fake_score` | Finite float in [0,1], not a calibrated probability |
| `model_version` | Nonblank string from actual compatible model metadata |
| `model_id` | Nonblank string identifying the actual model configuration |
| `text_truncated` | Strict bool describing ML preprocessing |

Backend adds the safely parsed request UUID and monotonic nonnegative integer
`processing_time_ms` around the Predictor call to build `PredictResponse`.
Timing includes ML preprocessing but excludes artifact loading and HTTP transport.
Do not supply invented IDs, timing or results when there is no loaded model.

`ModelNotReadyError` means absent, unavailable or incompatible model/artifacts.
Backend maps it to sanitized 503 `model_not_ready`, never its exception text.
Other programming/inference failures must not be mislabeled as invalid input or
converted into fake successes. Further internal-error policy belongs to model
integration; the current route never invokes inference.

## Lifecycle and dependency injection

`create_app(settings=None)` resolves configuration during ASGI lifespan startup,
sets `app.state.predictor = None`, and clears state on shutdown. It never probes
artifact files or imports ML libraries. `get_predictor(request)` returns the
installed provider or raises `ModelNotReadyError`. Future lifecycle integration
can set `app.state.predictor`; consumers can use FastAPI
`app.dependency_overrides[get_predictor]` during focused tests.

Current `/predict` resolves this seam but unconditionally reports unavailable,
even when overridden. This avoids enabling inference before transport safety is
implemented. `/health` reports `model_ready: false` regardless of injection or
configured paths; merely supplying an object is not proof of readiness.
There is no full mock or ready/loading/failed state machine (#9).

Proposed future model startup: ML supplies a compatible package; Backend loads
once, validates metadata and warms up before reporting readiness (#37/#38).
Backend owns resource lifetime/shutdown; ML defines resource release and thread
safety requirements. A synchronous CPU Predictor must run off the async event
loop. Worker count, serialization/thread safety and cancellation need ML review
before integration; this foundation starts one Uvicorn worker and performs no
inference. Client timeout does not prove cancellation of a running prediction.

## Ownership, dependencies and versioning

- **Backend:** HTTP/form parsing, token/policy, streamed byte limits, #23 image
  verification, correlation, timing, safe errors, DI and service lifecycle.
- **ML:** training/artifacts, model preprocessing and transforms, label mapping,
  threshold, result metadata, compatible ML dependency versions.
- **Extension:** `analyze.js` upload, client ID/timeout, stale-result handling and
  presentation; `service-worker.js` does not call `/predict`.

The initial requirements pin the resolved Python 3.10 backend and test packages.
There are no existing ML dependency manifests in this checkout, so **ML
compatibility is unconfirmed**. Do not add speculative Torch/CLIP/scikit-learn
pins or change training files. ML must supply their Python version and dependency
manifest before a combined environment can be tested.

Contract v0.1.0 is shared with `docs/api-contract.md`. Changes to the signature,
image representation, fields, preprocessing meaning or errors require coordinated
docs/schema/fixture updates and notice to Backend, ML and Extension before
adoption. Breaking changes increment the minor version while pre-1.0; compatible
clarifications increment the patch version. No approval is implied by versioning.
