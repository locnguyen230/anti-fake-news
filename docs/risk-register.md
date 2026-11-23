# Risk register — AFN-015 (2026-11-23)

Status means evidence verified in the default branch/issues, not an assertion that members have not worked elsewhere. Owner is responsible for obtaining the missing evidence. Target dates are **proposed**, not commitments.

| ID | Risk / observed gap | Severity | Unblock owner / source issue | Action & next checkpoint | Current state |
| --- | --- | --- | --- | --- | --- |
| R01 | Recovery count, usable images and provenance not independently verified; #3 reports checklist complete but remains open | High | DATA `locnguyen230`, #2/#3 | Supply immutable manifest checksum, counts, recovery summary and license notes for QA audit by W1 gate | Evidence pending |
| R02 | Group independence and final split 70/15/15 not established | High | DATA `locnguyen230`, #3/#18 | Supply stable event/source keys and split checksum; inspect leakage before any Train/Test | Blocked for acceptance |
| R03 | Experiment config/selection rules not checked in default branch | High | INTEGRATION `fulord26`, #4 | Sign protocol, seed 42, validation-only C/threshold and Test embargo | Open |
| R04 | CLIP CPU/processor revision, embedding dim, load time and RAM not verified | High | ML `0xDa1Vu`, #6 | Run real smoke on declared demo machine; report measured time/dimension/versions | Open |
| R05 | API v0.1.1 and Predictor interface remain proposed; language, EXIF, request limits, timeout unresolved | High | BACKEND `Phuc1232` with ML/EXTENSION, #8 | Collect cross-role approval and update schema/fixtures under version control | Open / recheck |
| R06 | Real `/predict` unavailable on default branch; mock is synthetic | High | BACKEND `Phuc1232`, #37/#38 | Keep real-mode 503 as truthful until artifact integration; no fake gate evidence | Known limitation |
| R07 | Extension DOM extraction and session may exist on an open PR but not verified in default branch | Medium | EXTENSION `ngnsusinn`, #10/#11 | Review PR #65 and execute sanctioned browser smoke on agreed fixtures | Open |
| R08 | Test-matrix IDs T01–T12 referenced but no detailed case definitions found in `DESIGN.md` §1–4 | Medium | QA `dangnguyen0512`, #14 | Review proposed IDs and evidence mapping with DATA; lock version after approval | Draft ready |
| R09 | Review windows, freeze timing and CODEOWNERS approvals not established for this QA gate | Medium | QA `dangnguyen0512` + owner `ngnsusinn`, #13 | Agree two local-time windows, end-of-week review and W4 Test lock | Team decision pending |
| R10 | `DEFINE.md` Vietnamese scope conflicts with contract note proposing English input | High | INTEGRATION `fulord26` + ML/EXTENSION, #4/#8 | Choose one documented language scope before final fixtures/metrics | Unresolved |

At each review window, update: evidence URL, measured impact, owner decision and next date. Escalate P0 blockers before spending contingency capacity; do not modify model or scope solely to pass a gate.
