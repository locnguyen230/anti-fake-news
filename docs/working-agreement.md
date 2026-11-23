# Working agreement — AFN-013 (draft for team approval)

Updated: 2026-11-23. Scope: four-week backlog AFN-001…AFN-060. This document records proposed working rules; the review windows and Test freeze date require explicit team agreement.

## Ownership and planning

GitHub issue assignees, verified 2026-11-23:

| Role | GitHub account | Backlog scope | Number |
| --- | --- | --- | ---: |
| DATA | `locnguyen230` | #2, #3, #16–18, #31–32, #46–48 | 10 |
| ML | `0xDa1Vu` | #5, #6, #19–21, #34–36, #49–50 | 10 |
| BACKEND | `Phuc1232` | #7–9, #22–23, #37–39, #52–53 | 10 |
| EXTENSION | `ngnsusinn` | #10–11, #25–27, #41–42, #55–57 | 10 |
| QA | `dangnguyen0512` | #13–15, #28–29, #43–44, #58–60 | 10 |
| INTEGRATION | `fulord26` | #1, #4, #12, #24, #30, #33, #40, #45, #51, #54 | 10 |

One accountable assignee per issue. Role reviewer for QA work: DATA, with `@ngnsusinn` retaining CODEOWNERS approval for **every** file. Specialist reviewers: DATA deliverables → QA, ML → BACKEND, BACKEND → ML, EXTENSION → QA, INTEGRATION → ML where issue specifies; the issue-specific reviewer takes precedence. Do not silently change assignees or treat a role label as a GitHub reviewer invitation.

Four iterations: W1 17–23 Nov, W2 24–30 Nov, W3 1–7 Dec, W4 8–14 Dec 2026 (Vietnam time). Issues use existing `week:1`…`week:4`, `area:*`, `priority:*` labels and GitHub milestones where assigned. The GitHub Issues list with filters `is:issue milestone:*`, `assignee:<login>`, `label:week:N`, `label:area:qa` is the **equivalent tracking board** until a team Project with custom Status / Priority / Estimate / Area fields is configured. This is not a claim that a GitHub Project or its views exist. Estimate remains the hours stated in each issue; preserve them when populating a future project.

Recommended statuses: Backlog → Ready → In progress → Review → Done, or Blocked when prerequisite evidence is missing. Track them in a project field when available; until then, record status explicitly in each issue comment/PR rather than guessing from open/closed state. Week and assignee views: filter the Issues page by week label and assignee; group by milestone for weekly review.

## Definition of Ready / Done

- **Ready**: owner assigned, scope and acceptance criteria readable, start dependencies checked, required contract version named; independent work may start while final acceptance inputs are outstanding.
- **Review**: link PR/commit, reproduction commands with actual outputs, negative cases, fixture provenance, changed interfaces, affected consumers, and reviewer request. All source data and credentials stay outside Git.
- **Done**: all deliverables exist, acceptance criteria verified with real evidence, tests run or limitations documented, reviewer approval recorded, blockers resolved, and CODEOWNERS review satisfied. An unchecked dependency or synthetic mock result cannot be counted as real-model evidence. Closed issues with recheck warnings are **not automatically accepted**.
- One issue has one assignee, one named role reviewer, and owner `ngnsusinn` as required CODEOWNER. Do not replace the code owner's approval with a role review.

## Review, blockers, handoff

1. Author raises focused PR with issue link, API/fixture versions and test evidence. Domain reviewer checks assumptions and behavior; owner reviews/merges under CODEOWNERS. Consumers of contract changes (Backend, ML, Extension, QA) are notified through linked issue/PR before rollout.
2. Proposed two daily review windows: **11:30** and **20:30** Asia/Ho_Chi_Minh. **Not yet approved**; team must confirm actual times. A blocked PR is flagged by the owner with the exact decision requested.
3. Blocker record format: `issue | symptom | prerequisite artifact/version | unblock owner | action | target date | evidence link | status`. Review blockers at each window; move to independent work without inventing data or relaxing gates.
4. Suggested contingency rule (requires agreement): reserve remaining capacity for high-impact P0 blockers first, then integration/regression, then documentation polish. Record hours used, approver, scope traded off, and impact in the issue; no automatic extra time or unapproved architecture change.
5. End-of-week checkpoint requires owners' evidence links and QA gate decision (Go / Conditional Go / No Go) with caveats. Suggested Test lock: **before AFN-050 begins in W4**, after model, preprocessing, threshold and split freeze (#49), and integrity sign-off (#58). **Exact calendar date/time must be chosen by the team**. Test is never used for tuning or UI benchmarks.

## Decisions requiring group sign-off

- Confirm actual review windows, weekly checkpoint times and Test lock instant.
- Confirm scope conflicts: `DEFINE.md` language statement versus proposed API's English preprocessing; current `DESIGN.md` contains only sections 1–4, so references to higher sections in issues are not present in that file.
- Approve API/inference interface v0.1.1 and image/EXIF, token, timeout, duplicate field and 12 MiB request decisions before treating it as stable.

Sources: [DEFINE](../DEFINE.md), [DESIGN](../DESIGN.md), [API draft](api-contract.md), [Issue #13](https://github.com/ngnsusinn/anti-fake-news/issues/13), [CODEOWNERS](../.github/CODEOWNERS).
