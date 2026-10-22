# Issue #24 — M3 readiness evidence and assessment

- Repository: `porntaned/ERP-for-Factory`; [Issue #24](https://github.com/porntaned/ERP-for-Factory/issues/24).
- Assessment date: 2026-10-22; main baseline `e6cd22c9bddd533b40d293dbad509076ae41172c`.
- Branch: `codex/review/m3-readiness`; [assignment](../assignments/issue-24-m3-readiness.md).
- Manager/verifier: `/root`. Source and live browser checks below are self-verification.
- Scope: main work item 2 only. Review existing M3 prerequisites, not implement M4.

## Recovery and evidence method

Remote and repository matched; original branch `codex/docs/readme-status`, head
`d215f403932b6d5d9db2bc2a105508f039f1a7d0`, clean tree. `git fetch origin` confirmed main
above; its tree equals the owner-checked PR #23 head. No open issue existed before #24.

Read AGENTS, TASKS, MULTI_AGENT, SCRUTINIZE, DEVELOPMENT, PROJECT, original M3 contracts,
RED/GREEN reports, independent reviews, current source/tests and the original post-PR12
audit on its preserved branch. No historical implementation, RED or database run is repeated.

Evidence sources are distinct:

- [Actual M3 Issue descriptions/criteria and states](issue-24-m3-issues-browser.txt):
  Issues #5/#7/#9/#11 are Closed/completed. Generic disabled checkbox placeholders in
  initial page captures do not prove that old acceptance checkboxes were checked.
  Acceptance is traced through criteria, implementation, tests, review and merged delivery.
- [Actual PR merged states](issue-24-pr-merges-browser.txt): M3 PRs #6/#8/#10/#12 and
  audit PRs #14/#16/#19/#21/#23 are Merged.
- [Actual audit Issue states](issue-24-audit-issues-browser.txt): #13/#15/#18/#20/#22
  are Closed/completed. Old issue bodies are historical contracts, not rewritten here.
- [Local Git proof](issue-24-git-history.txt): first-parent merge history with full
  merge/parent SHAs; all nine reviewed implementation SHAs below are ancestors of main.
- Historical RED/GREEN/reviewer reports below are reused records, not fresh retrieval
  of every historical job. Current main CI was inspected directly in this review.

## M3 acceptance matrix

### M3.1 — Item/UOM and Lot identity

| Delivery | Actual contract and current implementation | Tests, historical CI and independent review | Owner merge |
| --- | --- | --- | --- |
| [Issue #5](https://github.com/porntaned/ERP-for-Factory/issues/5), [assignment](../assignments/issue-5-item-uom.md) | [catalog models](../../catalog/models.py):12–45 and [migration](../../catalog/migrations/0001_initial.py): global UOM code; Organization-scoped Item code; protected Organization/base UOM; RAW/WIP/FINISHED check; non-null Unicode names; ASCII code format. Empty display names were explicitly allowed, not newly prohibited. | [Tests](../../tests/catalog/test_item_uom.py), [database/concurrency tests](../../tests/catalog/test_postgresql_constraints.py); [RED](issue-5-tdd-red.md) `139eb14a1d99ab2a31fb940cdcd093b93f6602c7`, 45 absent-contract cases; [GREEN](issue-5-green.md) / [review ship](../reviews/issue-5-item-uom-independent-review.md) at `05b7effe3eaba8a3b60b04aeee4542bd747c9308`, 96 passed. | [PR #6](https://github.com/porntaned/ERP-for-Factory/pull/6), `d31ac7a9f5286353ed05a46ccc6ce3be3c1678e1` |
| [Issue #7](https://github.com/porntaned/ERP-for-Factory/issues/7), [assignment](../assignments/issue-7-lot-identity.md) | [Lot model](../../inventory/models.py):7–20 and [migration](../../inventory/migrations/0001_initial.py): protected Item, required code, `(item, code)` uniqueness, code format. Same code on another Item is allowed. No Warehouse ownership or quantity field. | [Identity tests](../../tests/inventory/test_lot_identity.py), [database/concurrency tests](../../tests/inventory/test_postgresql_constraints.py); [RED](issue-7-tdd-red.md) `dab4b460bb5f0fea476a72d8c609746e02c708d1`, 19 failed/96 passed; [GREEN](issue-7-green.md) / [review ship](../reviews/issue-7-lot-independent-review.md) at `c66cab65bb0f1dcb7dd1131514446651fecc47cf`, 115 passed. | [PR #8](https://github.com/porntaned/ERP-for-Factory/pull/8), `b7a9bddd87d258c343d17abbc76e53de9a436dcd` |

Both contracts have separate Issue, assignment, real PostgreSQL RED/GREEN, independent
implementation review and merged PR. Code/type/null/FK/deletion/uniqueness/concurrent
duplicate cases are present. No unit conversion, stock quantity or movement is implied.

### M3.2 — Warehouse-scoped roles

- [Issue #9](https://github.com/porntaned/ERP-for-Factory/issues/9),
  [assignment](../assignments/issue-9-warehouse-role-grants.md): default Django User;
  [assignment model](../../access_control/models.py):15–38 with protected User/Warehouse,
  four valid roles and unique `(user, warehouse, role)`.
- [Policies](../../access_control/policies.py):31–72 validate supported role collections,
  reject non-operational/unsaved User instances, filter persisted-active Users and match
  exact user/Warehouse/roles. Query results are distinct and lazy.
- [Policy tests](../../tests/access_control/test_warehouse_role_policy.py),
  [assignment tests](../../tests/access_control/test_warehouse_role_assignment.py) and
  [database/concurrency tests](../../tests/access_control/test_postgresql_constraints.py)
  cover wrong/empty/invalid roles, inactive/anonymous/unsaved/unassigned users, superuser
  without grants, sibling Warehouse/Plant/Organization isolation, revocation, required
  references, deletion and concurrent duplicates. Later stale-user/unsaved-PK regressions
  are linked in the audit matrix below.
- [Historical RED](issue-9-tdd-red.md) `a58c6eb02efdb324c068343476bfc317f4c5657e`;
  [GREEN](issue-9-green.md) and [independent ship](../reviews/issue-9-warehouse-role-independent-review.md)
  at `23286336a752afd3791f4a41881f83f339bbe8a9`, 174 passed.
- [PR #10](https://github.com/porntaned/ERP-for-Factory/pull/10) merged at
  `6f6e06b2b99c7963593746ba6242e0737af252fe`.

These are internal read-policy interfaces. Materialized QuerySet caches and a separate
check-then-write sequence do not provide transaction-scoped authorization for a future
stock write. No login/session/API authentication, seeded demo accounts or inherited
superuser access was part of this contract.

### M3.3 — Quality disposition history

- [Issue #11](https://github.com/porntaned/ERP-for-Factory/issues/11),
  [assignment](../assignments/issue-11-lot-disposition-audit.md),
  [scope review](../reviews/issue-11-scope-independent-review.md): typed append-only
  history for an exact `(lot, warehouse)` pair, same Organization, missing state HOLD.
- [Model](../../quality/models.py):14–42 retains protected references, unique UUID
  request key, constrained states/nonblank reason and database-generated time.
- [Services](../../quality/services.py):84–179: getter returns latest event/default HOLD;
  transition locks Lot, persisted actor and exact QUALITY grant, checks current actor,
  resolves identical retries before validating a new command, rejects reused keys with
  changed payload, validates state/reason and appends inside one transaction.
- [Initial migration](../../quality/migrations/0001_initial.py) enforces append-only
  updates/deletes and valid insertion chains. [Identity/history repair](../../quality/migrations/0002_preserve_history_identity.py)
  uses authoritative event ordering, parent locks and referenced identity guards.
  [ALWAYS identity repair](../../quality/migrations/0003_authoritative_event_identity.py)
  rejects ordinary supplied IDs and preserves legacy sequence/history correctness.
- [Service tests](../../tests/quality/test_lot_disposition.py) and
  [PostgreSQL tests](../../tests/quality/test_postgresql_constraints.py) cover exact-pair
  HOLD default without an event, cross-Organization rejection, exact QUALITY authority,
  inactive/stale actors and revoked grants, no-op/stale/invalid state, blank reason,
  invalid UUID, exact retry/different-payload conflicts, protected references, direct
  invalid writes, immutable history, rollback, concurrent retries/distinct commands/
  direct inserts and parent-identity lock waits. Event-ID/migration tests are below.
- [Historical RED](issue-11-tdd-red.md) `78b2a8a8a00537ba70b9894e7443ddf792d91ee8`:
  174 passed/70 controlled absent-contract errors. [GREEN and repair evidence](issue-11-green.md)
  and [independent re-review ship](../reviews/issue-11-lot-disposition-independent-review.md)
  at `44b466fdd4e9d0134564c77aef7a316c1a2b8b7e`: 261 passed after the three recorded
  integrity defects were repaired; this is not the earlier 244-case initial verdict.
- [PR #12](https://github.com/porntaned/ERP-for-Factory/pull/12) merged at
  `9b1d182eb6867b70f076e95a63dc03f1814f00ec`.

The getter has no actor parameter, lock or movement side effect. Direct database
integrity constraints are not database-level User role authorization. Ordinary insert
identity protection does not cover deliberate administrative override/COPY/sequence
administration; the historical review documents those limits. Inspection records,
sampling, movement blocking and full QC are outside M3.3.

### M3.4 — separate delivery workflow

The four delivery rows/sections above provide actual separate Issue/Test/Review/PR
chains for Item/UOM, Lot, Warehouse roles and Quality. The fixes below likewise have
separate scoped Issues/PRs. M3.4's existing workflow requirement is evidenced; no new
implementation or retroactive rewriting of old acceptance checkbox states is needed.
Checking M3.4 does not itself accept overall M3 or authorize M4.

## Audit follow-up disposition matrix

Original [post-PR12 audit](https://github.com/porntaned/ERP-for-Factory/blob/codex/project-audit-after-pr12/docs/reviews/project-audit-after-pr12.md)
reviewed `9b1d182`; its historical `fix-then-ship` and deliberately RED reproduction
branch are preserved. The later fixes below resolve its five recorded findings;
this is not a claim that a test count proves absence of every possible future defect.

| Finding | Current resolution and focused coverage | Reviewed implementation / evidence | Completed owner delivery |
| --- | --- | --- | --- |
| 1 — persisted deactivation | Both policies query persisted active User state; [stale-instance/deferred tests](../../tests/access_control/test_persisted_deactivation.py) retained. | `abe63e154de62e7d37f3ff4c47252f6a88c07587`; [evidence](issue-13-policy-deactivation.md), [review ship](../reviews/issue-13-policy-deactivation-independent-review.md), full 264 passed historically. | [Issue #13](https://github.com/porntaned/ERP-for-Factory/issues/13), [PR #14](https://github.com/porntaned/ERP-for-Factory/pull/14), merge `eba63622495c6b065ad0abcd8e652676f9189d20` |
| 2 — unsaved colliding User PK | Shared helper rejects adding-state User; both interfaces have [six focused cases](../../tests/access_control/test_unsaved_user_policy.py), saved positive controls and retained Finding 1 checks. | `d132237211c5abdc509679da91b7b12566dff38c`; [evidence](issue-15-unsaved-user-policy.md), [review ship](../reviews/issue-15-unsaved-user-policy-independent-review.md), full 270 passed historically. | [Issue #15](https://github.com/porntaned/ERP-for-Factory/issues/15), [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16), merge `c62687b7ed60515de9424e69fe22ef43bbdfe81e` |
| 3 — supplied event ID | [Four ORM/SQL explicit-ID cases](../../tests/quality/test_event_identity.py) preserve release/HOLD/retry; [migration tests](../../tests/quality/test_event_identity_migration.py) cover legacy/empty sequence modes, reverse/reapply and exhaustion rollback. | `1c19981778b2f1cd45279de1b30945523d5827e0`; [evidence](issue-18-event-identity.md), [review ship](../reviews/issue-18-event-identity-independent-review.md), targeted 11/full 281 passed historically. | [Issue #18](https://github.com/porntaned/ERP-for-Factory/issues/18), [PR #19](https://github.com/porntaned/ERP-for-Factory/pull/19), merge `95d612bc41b4bda184598ba30f7072c4896f976d` |
| 4 — branch whitelist | [Workflow](../../.github/workflows/foundation.yml) selects `main`, `codex/**`, `feat/**` pushes and PRs to main; real nested-prefix/PR/main events recorded. | `56a0d80f05250751b3e5025b1c28ec5f6137d60c`; [evidence](issue-20-ci-triggers.md), [review ship](../reviews/issue-20-ci-triggers-independent-review.md). | [Issue #20](https://github.com/porntaned/ERP-for-Factory/issues/20), [PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21), merge `a294080133cc31ee6ce0b0e1fc808280d669f203` |
| 5 — README status | [README](../../README.md) is dated, links actual milestones/main evidence and retains unfinished scope. | `cf9f010d212261ddc2e2c8a23bc60dfdc18ebf7b`; [evidence](issue-22-readme-status.md#owner-authorized-merge), [review ship](../reviews/issue-22-readme-status-independent-review.md); Markdown/render checks recorded. | [Issue #22](https://github.com/porntaned/ERP-for-Factory/issues/22), [PR #23](https://github.com/porntaned/ERP-for-Factory/pull/23), merge `e6cd22c9bddd533b40d293dbad509076ae41172c` |

## Current exact-main verification

Actual [Foundation run 39754340827](https://github.com/porntaned/ERP-for-Factory/actions/runs/39754340827),
job 119742446278, was triggered by push to main at
`e6cd22c9bddd533b40d293dbad509076ae41172c`. It succeeded: **281 passed in 5.52s**.
[Selected visible DOM proof](issue-24-main-ci-browser.txt) records event/ref/full SHA,
Python 3.14.8, Django 5.2.18, psycopg 3.3.6, `vendor=postgresql` and PostgreSQL
`18.6 (Debian 18.6-1.pgdg12+2)`.

All retained configuration, migration-state, fresh-migration, Ruff and three targeted
regression steps completed successfully in that job. Individual targeted outputs were
collapsed here, so no new individual targeted counts are inferred. Runtime and full
suite were expanded. This is an existing main run re-inspected through the browser,
not a new verifier database execution or a run of the later documentation commit.

Actual retained CI commands are in [Foundation](../../.github/workflows/foundation.yml):
locked uv sync, version prints, `uv run python manage.py check`, real PostgreSQL
connection/SHOW server_version, `makemigrations --check --dry-run`, `migrate --noinput`,
`uv run ruff check .`, three existing targeted pytest commands, `uv run pytest -q --tb=short`.
Local review used `git fetch origin`, merge history/ancestor commands in the Git proof,
`rg`/source reads and diff/link checking. No SQLite, mocks, new tests or new RED claim.

## Readiness assessment and next boundary

Within the implemented M3 contracts and inspected paths, no unresolved blocker from
the five recorded audit findings or new confirmed M3 defect was found. The available
evidence supports **owner review of technical M3 readiness for separately scoped M4
planning**. It does not establish operational Inventory acceptance or production readiness.
The independent readiness review and owner decision remain separate gates.

Before an M4 implementation, a separate approved Issue/contract must define:

1. Inventory-owned quantity/ledger invariants, base-UOM quantity rules, nonnegative
   stock, synthetic receipt and same-Plant transfer scope. Existing Item/Lot identity
   and base-UOM references are inputs; no conversion/stock semantics are supplied by M3.
2. Write-time persisted authorization for each movement and exact source/destination
   Warehouse role rules. A cached policy result is not authority for a later write.
3. Atomic movement/state checks and lock coordination with Quality transitions. A
   snapshot getter alone cannot prevent a race with HOLD. Quality owns the decision;
   Inventory must enforce eligibility at its movement boundary.
4. Inventory's own idempotency/conflict/rollback/concurrency protocol. Quality's UUID
   keys protect Quality commands only. Posted movement corrections must retain history
   and reference their originals according to AGENTS/domain ownership.

These are future M4 design obligations, not newly claimed defects or features delivered
by this review. Inspection workflows, UI, Manufacturing and valuation remain excluded.
No real stock adjustment or privileged integration is authorized by a readiness verdict.

## Handoff status

M3.4 can be evidenced from the matrix; overall M3 remains pending owner acceptance of
the readiness PR. Do not start M4 on the basis of this report. This documentation-only
review changes no application/test/schema/workflow/dependency. No merge or deployment.
Final independent Scrutinize, exact reviewed documentation SHA and owner-review PR
are recorded in the handoff before delivery.
