---
name: afn-issue-implementer
description: Implement, test, and hand off one or more GitHub issues in ngnsusinn/anti-fake-news. Use when the user asks to work on AFN-xxx or GitHub issue #N, fix a blocker, implement a feature, verify acceptance criteria, or plan an issue. Reads current issue/docs/code, respects dependencies and file ownership, and produces verifiable evidence.
---

# Anti-Fake-News Issue Implementer

Execute repository issues end-to-end, with narrow scope and auditable results. **The issue number and current repository state are inputs; this skill must work for future issues not yet known.**

## Inputs

- Issue identifiers: `#N`, `AFN-NNN`, or several identifiers; resolve backlog IDs to actual GitHub issues. Never assume AFN number always equals GitHub issue number.
- Repository: default `ngnsusinn/anti-fake-news`, unless the user explicitly specifies another repository.
- Mode: `plan` if asked for planning only; otherwise `implement`. In `review` mode, inspect and report without changing code.
- User instructions and any current task-specific constraints take precedence over optional patterns in this skill.

## Mandatory workflow

### 1. Discover and establish the truth

1. Open the **current** GitHub issue(s) including title, body, checklists, acceptance criteria, comments, state, links, labels, and dependencies. If GitHub access fails, use the locally provided issue text and clearly flag missing live verification.
2. Inspect working tree: `pwd`, `git status --short`, current branch, file tree, tests, dependency tooling. Do **not** discard user changes, use destructive resets, or overwrite unrelated edits.
3. Read current `README.md`, `DEFINE.md`, `DESIGN.md`, `DIAGRAMS.md` and relevant files such as `docs/api-contract.md`, `docs/inference-interface.md`, `docs/implementation-issues-7-8.md` **if present**. Search for task-specific source and tests. These documents may evolve and conflict: do not silently assume an earlier snapshot is current.
4. Build a compact **requirements matrix**: requirement, source (issue/doc), intended code location, verification, dependency/reviewer, status. Distinguish existing behavior, requested behavior, proposal and future work.
5. If documents conflict, prefer an explicitly superseding decision or approved current contract. Otherwise preserve existing public interfaces, note the conflict, and proceed only with safe independent work. Do not invent product decisions (language, limits, model pipeline, auth policy, etc.).

### 2. Dependency and ownership audit

- Distinguish **start prerequisites** from **Done/review prerequisites**. Work independently on non-blocked parts; record final blocker with owner and required version/artifact.
- Identify consumers of changed contracts (Backend, ML, Extension, QA). Notify/record contract changes and update tests/fixtures/docs together; never silently break callers.
- Stay within the requested issues. Don't implement adjacent future issues just because their code is nearby. Add only minimum safe infrastructure needed to satisfy acceptance criteria.
- Don't modify an ML-owned model loader, checkpoint, training pipeline, data manifest/splits, or an Extension-owned file without the task expressly requiring it or an established handoff.

### 3. Plan before editing

Write a short work plan in the working context (not an unnecessary permanent file) covering: exact files, sequence, tests, risks, compatibility, and what will not be done. For multiple issues, order by dependencies and group shared changes without duplicating code. Wait for the user to confirm the plan before proceeding with the next steps.

### 4. Implement minimally and safely

- Follow the repo's language, naming, layout, package/version, testing, and existing dependency-injection patterns. Reuse code and interfaces; no speculative architectural rewrite.
- Preserve end-to-end contracts and JSON error shape. Keep interface versions/fixtures synchronized when changed.
- No fake success: missing model artifacts or real-mode inference failure must not silently fall back to a mock or report ready.
- Mock/test doubles must require an explicit dev/test opt-in, be clearly identifiable, and never be promoted into evidence of real ML inference.
- Protect credentials, raw articles/images, user data, checkpoints and machine paths. Never log or commit secrets, `.env`, raw data, model weights, or caches. Avoid external AI calls unless an issue explicitly changes the approved architecture.
- Respect the actual scope of the issue: full enforcement belongs to its assigned issue; a skeleton is not a completed implementation.
- When a requirement changes the public interface, update examples, contract docs and fixtures in the same change; seek review where mandated.

### 5. Verify with evidence

1. Run relevant tests plus regression tests for impacted modules. Use repository commands; if unavailable, write meaningful tests and run them if the environment permits.
2. Check lint/type tools if configured, dependency integrity, `git diff --check`, import/startup smoke, and meaningful negative/error cases.
3. Verify each acceptance criterion against code or test output. Never label unrun tests as passed, and never use mock results as evidence of true model accuracy.
4. Check source diff for unintended files and secrets. Do not claim approval/PR/commit exists unless actually created.
5. If a tool or dependency is unavailable, state exactly what couldn't be verified and why; do not silently replace a failed test with a weaker claim.

### 6. Handoff

Report concise sections:
- Issues addressed and scope.
- Files changed, behavior added, and interfaces impacted.
- Acceptance criteria table: `PASS / PARTIAL / BLOCKED / NOT RUN`, with specific evidence.
- Commands run and actual outcomes.
- Open blockers/dependencies, reviewer ownership, and follow-on issue boundaries.
- Pending decisions and security/privacy considerations.
- Commit/PR URL **only if one was actually created**.

Do not auto-close issues, assign reviewers, push, merge, or publish releases unless explicitly requested. Editing local code and running tests are allowed in `implement` mode. Respect environment permissions and ask approval before externally consequential actions.

## Project-specific guardrails (verify with live docs)

- Typical system: Chromium Extension → local FastAPI → injected Predictor → offline-trained TF-IDF / CLIP ViT-B/32 / `scipy.sparse.hstack` / Logistic Regression → JSON. **Confirm against current repo; this is context, not immutable contract.**
- The project historically uses `GET /health`, `POST /predict`, `X-Demo-Token`, multipart text/image, model-ready handling, and a local `127.0.0.1` backend. Do not assume these are already enforced just because config/docs exist.
- Environment settings historically include `AFN_HOST`, `AFN_PORT`, `AFN_DEMO_TOKEN`, `AFN_EXTENSION_ORIGIN`, `AFN_MODEL_ARTIFACT_PATH`, `AFN_MAX_REQUEST_BYTES`. Read actual current config before editing.
- Maintain offline train/evaluation separation from online inference; never fit on validation/test or retrain inside a request. Test data must not be used for selecting models/thresholds.
- Do not claim the model performs fact verification, image-manipulation detection or independent cross-modal consistency checking unless newly implemented and validated.
- The README and project documents have evolved; current GitHub content can differ from older copies (including target language). Treat discrepancies as a decision to surface, **not** permission to silently override.

## Issue-specific recipes

Read [references/issue-recipes.md](references/issue-recipes.md) for current known backlog relationships and a minimal interpretation of #7/#8/#9. This is **illustrative, not a substitute for fetching the live issue**. For any later issue, apply the same workflow, deriving requirements entirely from its current body and repository.

## Completion standard

A task is complete only when its requested deliverables exist, acceptance criteria have evidence, tests were executed or explicitly blocked, and mandated review status is accurately represented. Code-complete is not the same as GitHub issue Done.
