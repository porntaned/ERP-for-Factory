# Issue #29 — synthetic stock receipt evidence

[Issue](https://github.com/porntaned/ERP-for-Factory/issues/29) ·
[assignment and role boundaries](../assignments/issue-29-stock-receipt.md).

Current status: **M4.2 accepted and merged; Issue #29 completed** on 2026-10-23.
See [owner-authorized merge and main push](#owner-authorized-merge-and-main-push).
Earlier handoff/review statements retain their historical pre-merge scope.

## Recovery and approved scope

2026-10-23: verified origin `https://github.com/porntaned/ERP-for-Factory.git`,
clean local branch `codex/docs/m41-post-merge` at `0824e08`. Git fetch and the
GitHub browser verified main `21ab14082fb18a99bfa1fb1c3a5061323bfadc33`, merged
PR #28 and successful [main CI #99](https://github.com/porntaned/ERP-for-Factory/actions/runs/39896584392).
No open Issues existed before creating #29. Created feature branch
`codex/inventory/synthetic-receipt` at that main. Owner approved exact WAREHOUSE
authority, unchanged HOLD/default HOLD/RELEASED and receipt UUID retries. No UI,
transfer, adjustment, valuation, real data, merge or deployment authorized.

Root implements application code and observes CI; separate agent
`/root/m42_tests` wrote receipt tests; `/root/m42_contract_review` performed read-only
design review. It recommended existing parent SHARE locks and a savepoint spanning
both ledger append and receipt insert. Evidence is batched; independent reads/tests
were developed in parallel, while test/repair/final-review gates remain sequential.

## Controlled PostgreSQL RED

Test-only commit `1571c6ec1750c5389d565b7edcb21579791704e2` contains assignment,
receipt test modules and one targeted step in the existing Foundation workflow.
[Run #100](https://github.com/porntaned/ERP-for-Factory/actions/runs/39908761378),
[job 120266646705](https://github.com/porntaned/ERP-for-Factory/actions/runs/39908761378/job/120266646705),
failed at `uv run pytest -q tests/inventory/test_stock_receipt*.py --tb=short`:
**55 errors in 1.20s**, reporting `M4.2 receipt contract absent: controlled RED`
after resolving the absent `inventory.StockReceipt` contract.

The real PostgreSQL environment, Django configuration, drift/fresh migration and
Ruff steps succeeded before the receipt step. Expanded connection logs recorded
`vendor=postgresql`, server **18.6 (Debian 18.6-1.pgdg12+2)**; existing ledger tests
were **121 passed in 8.02s**, with retained auth/Quality regressions preceding them.
The full-suite step was not executed after this expected failure. Later tests are
not retroactively attributed to this 55-case RED run.

## Implementation and local checks

Application/test commit `0a96eda80107f088d043c0ed47683ae6e6ddbd69` adds a normalized
`StockReceipt` linked to an immutable positive ledger entry, receipt guards and the
authorized `receive_stock` transaction. UUID uniqueness plus a savepoint enclosing
both inserts prevents an extra delta on a cross-Lot retry conflict. Quality history
is untouched; Lot locking coordinates with existing transitions.

Windows PowerShell local commands used the existing `.venv` and synthetic
collection-only settings, with no `.env` or credential changes:

```powershell
.venv/Scripts/ruff.exe check .
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe -m pytest --collect-only -q tests/inventory/test_stock_receipt.py tests/inventory/test_stock_receipt_concurrency.py
git diff --check origin/main...HEAD
```

Ruff, Django check, model-state comparison and diff checks passed. Final collection
reported **87 tests collected in 0.22s**. Migration generation/model-state commands
warned that local PostgreSQL at 127.0.0.1 was unavailable; this is NOT database
verification. Database behavior and migration consistency evidence must come from
the disposable real PostgreSQL CI service. No local PostgreSQL execution claimed.

## Storage and operational limits

The ledger supplies receipt actor, pair, exact base-UOM quantity, exact reason and
database-generated time. Receipt request UUID and ledger linkage are immutable;
ordinary supplied receipt IDs are rejected. Tests can use direct storage writes to
prove invariants; those writes are not an authorized business posting interface.
Privileged trigger disabling, TRUNCATE and DB administration remain outside the
ordinary-write boundary. No generic movement API or full M4.4 completion is claimed.

Receipt into an existing RELEASED pair keeps RELEASED; this is not fresh inspection
of each delivery. Independent receipt commands for one Lot serialize across its
Warehouses, and commands for one actor also serialize on its User row. These are
intentional small-protocol tradeoffs; no throughput benchmark is claimed.

## PostgreSQL GREEN and independent review

[Foundation #101](https://github.com/porntaned/ERP-for-Factory/actions/runs/39909020029),
[job 120267442017](https://github.com/porntaned/ERP-for-Factory/actions/runs/39909020029/job/120267442017),
**Success** on implementation/test commit
`0a96eda80107f088d043c0ed47683ae6e6ddbd69`. The checkout log's
`git log -1 --format=%H` records that exact SHA. Expanded runtime logs recorded
Python **3.14.8**, Django **5.2.18**, psycopg **3.3.6**, and PostgreSQL
**18.6 (Debian 18.6-1.pgdg12+2)**. Workflow environment: Ubuntu 24.04,
`postgres:18.6-bookworm`, uv 0.13.1 and locked dependencies.

| Actual command | Observed result |
| --- | --- |
| `uv run pytest -q tests/inventory/test_stock_receipt*.py --tb=short` | **87 passed in 3.86s** |
| `uv run pytest -q --tb=short` | **489 passed in 17.32s** |

The successful job also ran Django checks, PostgreSQL connection, model/migration
drift check, migrations on fresh PostgreSQL, Ruff, retained deactivation/unsaved-user/
event-identity regressions and the targeted M4.1 ledger suite. Full suite is the
existing 402 tests plus 87 new receipt cases; no unrelated tests were removed.

The new tests cover exact maximum quantity and distinct receipts; wrong/unsaved/
missing/stale actors and parents; same-Organization/current identity checks; exact
Warehouse roles; authorized retry/conflict; both-write and outer rollback; raw SQL
unique/not-null/missing/nonpositive linkage and immutable identity; supported
isolation; and migration reverse/reapply restoring actual guards while retaining
the existing ledger. Concurrency tests use observed `pg_blocking_pids` for same-key
and cross-Lot collisions, auth changes, Quality transitions and parent identity
mutations. Injected receipt-insert failure is a deliberate failure boundary after
a real ledger insert, not a mocked database behavior claim.

After GREEN, independent read-only agent `/root/m42_final_review` reviewed
`0a96eda` against `21ab140`: **ship**, no actionable defects. It traced validation,
parent lock order/modes, persisted actor/grant before retries, exact payload matching,
global UUID conflict rollback, DB receipt guards, migration reversal and Quality
serialization. [Formal independent source review](../reviews/issue-29-stock-receipt-independent-review.md).
The reviewer did not run PostgreSQL or retrieve live CI; root inspected the CI.
Later handoff documentation commits are outside that reviewed application/test SHA.

## Manager self-Scrutinize and handoff

- **Intent/smaller solution:** one receipt UUID/type record references the existing
  authoritative ledger payload. No duplicate quantity/actor/pair/time fields,
  editable balance projection, generic movement framework or UI.
- **Trace:** approved Issue/assignment → dynamic RED contract → service validation →
  Lot/Item/Warehouse/Plant locks → current User/exact WAREHOUSE grant → retry lookup →
  savepoint containing both writes → ledger/receipt triggers → snapshot balance.
  Quality uses the shared Lot lock and retains sole ownership of disposition.
- **Verify:** PostgreSQL RED/GREEN and exact commands/SHAs above; Ruff, Django check,
  collection and diff checks locally. Source design and final reviews are separate
  from root's CI observation/self-verification. No implementation repair was needed
  after the first GREEN attempt; one out-of-scope proposed TRUNCATE test was removed
  before RED because administrative operations are outside the contract.
- **Report/verdict:** `ship` for an owner-review PR. Intentional existing-Lot Quality
  policy and serialization/privileged-write limits are documented above. M4.2 remains
  pending owner acceptance and merge; M4.3–M4.7 remain unstarted. No merge/deployment.

Handoff files: inventory model/service/migration 0004; two receipt test modules;
one targeted workflow step; assignment, this evidence, independent review and
README/TASKS/approved-proposal status. Next responsible role: owner PR review.

## Owner-authorized merge and main push

The owner explicitly authorized merging [PR #30](https://github.com/porntaned/ERP-for-Factory/pull/30).
GitHub records merge commit **`5701d51dfe48558c6dab21e1e3525de3291b452e`** into
`main` on 2026-10-23 at **13:18 Asia/Bangkok**, after both PR-head checks passed.
Live [Issue #29](https://github.com/porntaned/ERP-for-Factory/issues/29) is closed as
**completed** through PR #30; all five delivery checks already have linked evidence.
This supersedes the pending-owner statements in the historical handoff above.

Post-merge recovery used Windows PowerShell:

```powershell
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
git fetch origin
git switch -c codex/docs/m42-post-merge origin/main
git rev-parse HEAD
git diff --exit-code e5e5f67c662b289911788c03aefcbadf033bbbda HEAD
```

Verified repository URL `https://github.com/porntaned/ERP-for-Factory.git`, clean
local branch `codex/inventory/synthetic-receipt` at `e5e5f67`, and fetched main
advancing from `21ab140` to the merge SHA. The documentation branch starts at that
merge. Tree comparison against the merged PR head exited 0 with no output: no
application implementation was repeated or changed.

The latest live Actions run at recovery was
[Foundation #104](https://github.com/porntaned/ERP-for-Factory/actions/runs/39910705968),
**push / main / Success**. [Job 120272796488](https://github.com/porntaned/ERP-for-Factory/actions/runs/39910705968/job/120272796488)
checked out the exact merge SHA above (`git log -1 --format=%H`), recorded
`vendor=postgresql`, server **18.6 (Debian 18.6-1.pgdg12+2)** and succeeded.
The existing workflow uses Ubuntu 24.04 and disposable `postgres:18.6-bookworm`.

| Actual main-push command | Observed result on merge SHA |
| --- | --- |
| `uv run pytest -q tests/inventory/test_stock_receipt*.py --tb=short` | **87 passed in 4.15s** |
| `uv run pytest -q --tb=short` | **489 passed in 18.55s** |

Django checks, PostgreSQL connection, model/migration drift, fresh migrations,
Ruff and retained auth/Quality/ledger regressions also passed in the same job.
These are manager-observed CI results; no new local PostgreSQL execution or new
independent review of application code is claimed. The existing independent source
review remains scoped to implementation/test SHA `0a96eda`.

### Documentation self-Scrutinize

Intent: reconcile owner-accepted M4.2 on existing status surfaces, preserving
historical test/review evidence. Traced PR merge → Issue completed → main checkout
SHA/runtime/test logs → README/TASKS/assignment/proposal links. The smallest change
updates status and appends this addendum; no runtime/test/workflow changes are needed.

Verification on the uncommitted documentation tree based on `5701d51`:
`git diff --check` passed; `.venv/Scripts/python.exe -` with an inline
`pathlib`/`re` check passed for 5 Markdown files, 121 existing local link targets,
balanced fences and milestone gates (M4.1/M4.2 checked, M4/M4.3–M4.7 unchecked).
`git diff --stat` confirmed only the five documentation files changed.

Self-review verdict: **ship** for a documentation PR. M4.1 and M4.2 are complete;
M4 overall stays unchecked, M4.3–M4.7 remain unstarted. No UI, merge of this
documentation PR, deployment or new feature is included in this reconciliation.
