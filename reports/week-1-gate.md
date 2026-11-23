# Week 1 feasibility gate — AFN-015

**As of:** 2026-11-23 (Asia/Ho_Chi_Minh)  
**Decision: CONDITIONAL / NOT SIGNED OFF.** Independent W2 tasks may start, but the W1 feasibility gate cannot be marked Done without real recovery and CPU evidence, a reviewed contract and formal team approval.

## Evidence review

| Gate input | Source/status observed | Decision |
| --- | --- | --- |
| Pilot ≥30 URLs and recoverable article+image counts | #2/#3 tracked; no validated numeric report incorporated into this gate | Pending DATA evidence, do not invent sample counts |
| Target 200–500 valid samples; labels/groups and missing-image reasons | `DEFINE.md` sets target; #3 remains open despite checked tasks | Pending manifest, checksums, count reconciliation |
| Three configurations and validation-only model selection | `DESIGN.md` §4 outlines three configurations; #4 open | Pending approved experiment protocol |
| CLIP ViT-B/32 CPU load/memory/embedding evidence | #6 open | Pending measured smoke output on demo device |
| API/Extension contract | `docs/api-contract.md` and `docs/inference-interface.md` v0.1.1 proposed; #8 marked recheck | Pending joint Backend/ML/Extension approval |
| Backend scaffold | Default `README.md` describes local FastAPI with `/health` not-ready and real `/predict` 503; dev/test mock only on explicit opt-in | Scaffold present; not a real inference pass |
| Extension smoke | #10/#11 open; PR #65 was open at audit time | Review/merge/check smoke and evidence before claiming integrated flow |
| QA matrix and team workflow | Draft `docs/test-plan.md`, `tests/fixtures/README.md`, `docs/working-agreement.md` supplied by this change | Await DATA role review and CODEOWNERS approval |

## Reproducible checks still to run

1. On a checkout with dependencies, run `cd backend && python -m pytest -q` and capture exact pass/fail count, Python version and commit SHA.
2. Run `python backend/tests/smoke_local.py` **from `backend/`** using an isolated local environment, then explicit mock mode only for contract development; record 200 `/health` and 503 real-mode `/predict` as their actual meanings. Do not count a mock 200 as model quality.
3. Run Extension browser smoke from the reviewed branch/merge commit after reviewing PR #65; capture tab/manual fallback and relative image URL behavior.
4. Obtain actual recovery logs, independent group count, source/license report and checksum from DATA; verify `input = valid + excluded + pending` with explanations.
5. Obtain CLIP checkpoint/revision, frozen inference smoke on demo CPU, actual embedding dimension, load time and memory from ML.

No commands above are represented as executed by this gate. All quantitative measurements remain unknown until linked to a reproducible source.

## Decision and actions

- **No Go for W1 final acceptance / real-model demonstration.** There is no trustworthy evidence in this gate to claim 200 valid samples, 30 pilot URLs, CLIP CPU readiness, or stable API sign-off.
- **Conditional Go for independent W2 development**: fixture/schema review, synthetic contract tests, extension UX and split validator work may proceed, preserving existing contract version and making no premature Test use.
- **Blockers:** R01/R02 DATA `locnguyen230` (#2/#3); R03/R10 INTEGRATION `fulord26` (#4); R04 ML `0xDa1Vu` (#6); R05 BACKEND `Phuc1232` with ML/EXTENSION (#8); R07 EXTENSION `ngnsusinn` (#10/#11); R09 QA `dangnguyen0512` plus owner for review calendar (#13). See [risk register](../docs/risk-register.md).
- **Required sign-off:** DATA reviewer and `@ngnsusinn` CODEOWNER; record decision, dates, real evidence links and affected scopes in the PR/issue before marking #15 Done. W2 work must not be blocked merely because this aggregate W1 gate remains unsigned.

Source documents: [DEFINE](../DEFINE.md), [DESIGN](../DESIGN.md), [API contract](../docs/api-contract.md), [Issue #15](https://github.com/ngnsusinn/anti-fake-news/issues/15).
