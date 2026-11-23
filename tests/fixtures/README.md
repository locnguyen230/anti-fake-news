# QA fixture registry (AFN-014)

Owned by QA. Synthetic samples only. No credentials, downloaded articles, real dataset Test rows, model weights or licensed images are committed. For actual research Test, track only an authorized immutable manifest/hash separately; never use it for development or tuning.

| Namespace | Origin | Purpose | Expected behavior |
| --- | --- | --- | --- |
| `qa/v0.1.1/empty-text.json` | Hand-written synthetic data, 2026-11-23 | T04 whitespace-only body | Reject as invalid; no prediction |
| `qa/v0.1.1/request-valid-fields.json` | Hand-written synthetic data, 2026-11-23 | T06 multipart *field blueprint* | Request uses UUID + text + one uploaded image; not a runnable multipart body |
| `backend/tests/fixtures/api/v0.1.1/` | Existing Backend development mock/contract fixtures | Parser/schema development | Not proof of real inference or research Test result |

Generate rather than commit heavy or potentially copyrighted data:

1. **Long body**: generate `"a".repeat(50001)` as text; validate against the agreed 50,000-codepoint ceiling; include a 501-codepoint title edge case. No real article needed.
2. **Corrupt image**: create a local file containing plain UTF-8 `not-an-image` but with `.png` name; try both `image/png` and `text/plain` MIME. Never assume the current mock rejects decode failures: full decoder belongs to #23.
3. **Too-large image**: generate a disposable >10 MiB buffer as test input in a temporary directory, do not commit it. Expected final API 413; whole-request 12 MiB remains proposed.
4. **EXIF orientation**: generate or obtain an original, permission-cleared JPEG with orientation=6 and record author/license and expected upright dimensions. Not bundled until verified; #23 owns actual normalization.
5. **Race, timeout and CORS**: two distinct UUIDs, deferred response A/B, a server that closes/delays connections, and an unauthorized browser origin. Store only sanitized traces. Ensure origin/token checks are evaluated independently.

Version rule: contract changes require explicit version bump, synchronization of request examples, test matrix and fixtures, and notification to Backend/ML/Extension. None of these files are scientific Test samples.
