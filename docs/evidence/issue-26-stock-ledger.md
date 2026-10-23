# Issue #26 — stock ledger verification

Repository `porntaned/ERP-for-Factory`; [Issue #26](https://github.com/porntaned/ERP-for-Factory/issues/26).
[Contract/assignment](../assignments/issue-26-stock-ledger.md).

Current status, verified 2026-10-23: **M4.1 merged and Issue #26 completed**.
See the [post-merge addendum](#owner-merge-and-main-push-ci). Earlier handoff and
review statements describe their pre-merge state; they are retained as history.

## Recovery

2026-10-22: verified remote, branch `codex/review/m3-readiness`, clean HEAD
`6861058eb5663af2e0c59cd56224abcccfa5f935`. Fetch confirmed main
`e806b6491d962f8124cc17d902eca2a692485ad1`. Browser verified PR #25 Merged,
Issue #24 Closed/completed, zero open Issues/PRs before Issue #26 creation.
Feature branch `codex/inventory/stock-ledger` starts at that main. M3's stale pending
checklist was reconciled from the actual merge, not by repeating implementation.

## PostgreSQL RED

Commit `e4848a9a962d2972141bdc874f464eb899a6aa14` contains tests/assignment only.
[Foundation run 39793972919](https://github.com/porntaned/ERP-for-Factory/actions/runs/39793972919),
[job 119876609506](https://github.com/porntaned/ERP-for-Factory/actions/runs/39793972919/job/119876609506):
**281 passed, 56 errors in 6.12s**. All new failures explicitly report the absent M4.1
contract; old tests pass. Dependency setup, Django check, PostgreSQL connection,
migration checks/fresh migration, Ruff and retained targeted regressions reached the
full test step successfully. [Visible browser evidence](issue-26-red-browser.txt)
records Python 3.14.8, Django 5.2.18, psycopg 3.3.6 and PostgreSQL 18.6
(Debian 18.6-1.pgdg12+2), plus absent-contract errors/final summary.

Executed workflow command: `uv run pytest -q --tb=short`. The fixtures deliberately
resolve the absent model/query dynamically; this is controlled missing-behavior RED
after successful database setup, not an unhandled import/environment failure.

Local `.venv/Scripts/python.exe -m pytest --collect-only -q` on the two new modules
collected 56 cases; Ruff and `git diff --check` passed. Local synthetic configuration
was used for collection only. No local PostgreSQL service/configuration is available;
local migration generation reported connection failure while successfully generating
model state. Real database claims rely on GitHub's disposable PostgreSQL service.

## Scope/RED review repair

Independent read-only reviewer `/root/m41_scope_review` reviewed `e4848a9...`:
scope `ship`, RED-test intent `fix-then-ship`. Tests were strengthened to isolate
negative range from overdraft; cover five parent identity edges in both transaction
orders; and observe the exact blocker with `pg_blocking_pids`. Server timestamp bounds
and parent isolation/no-op controls were added. These later tests are not relabelled
as part of the original 56-case RED execution.

Reviewer confirmed the parent identity guard also needs READ COMMITTED even without
history, otherwise a fixed snapshot can miss a newly committed append. This design
extension is documented in the assignment. The scope reviewer did not execute tests.

## Design rationale and limits

The smallest design uses immutable entries plus indexed per-pair SUM, no separate
mutable balance projection. Lot locking serializes entries across warehouses for that
Lot; this intentionally trades throughput for a small auditable protocol compatible
with Quality. Long histories require linear work per balance computation; pagination,
caching/projections and throughput optimization are future measured work.

[PostgreSQL numeric documentation](https://www.postgresql.org/docs/18/datatype-numeric.html)
explains why unconstrained numeric plus explicit checks is needed to reject excess
precision rather than rounding it. [Volatility documentation](https://www.postgresql.org/docs/18/xfunc-volatility.html)
describes fresh snapshots in volatile function queries; write operations still reject
higher isolation levels. Database administration, trigger disabling and TRUNCATE are
outside the documented ordinary-write boundary.

There is no posting command, role authorization, HOLD eligibility enforcement,
idempotency or reversal here. Direct inserts in tests prove storage invariants only.
The read query is an internal snapshot, not a reservation. M4.2–M4.7 remain pending.

## Implementation, repairs and final PostgreSQL evidence

The branch adds `StockLedgerEntry`, an exact PostgreSQL numeric quantity field,
`get_stock_balance`, migrations 0002/0003 and focused tests. Migration 0002 enforces
append-only history, nonnegative pair totals, persisted same-organization parents,
READ COMMITTED writes and identity-edge guards. Migration 0003 makes the three direct
ledger foreign keys immediate `RESTRICT` and guards Item/Plant deletion and PK changes.
This closes deletion followed by recreation with the same PK, including zero-balance
history and one-statement replacements. Tests exercise both orders of observed lock
contention, rollback, fixed snapshots and migration reverse/reapply.

The first implementation run at `17c10a7afb54d3844ef9b631181e610960ad8a89`
([run 39797622814](https://github.com/porntaned/ERP-for-Factory/actions/runs/39797622814))
had **74 passed, 1 failed** in the targeted suite: the explicit identity test expected
`IntegrityError`, but PostgreSQL reports a different `DatabaseError` subclass. That
test assertion was corrected. Independent source review then identified the missing
locked-parent `NULL` path under deferred foreign keys. Commit
`3b0cc24d972df5dbe53576c99f68760c943a9041` fixed the path and added regressions;
[run 39798470416](https://github.com/porntaned/ERP-for-Factory/actions/runs/39798470416)
passed **77 targeted in 4.56s and 358 full in 8.37s**. These results predate the
lifetime repair. Browser records: [first attempt](issue-26-first-green-attempt-browser.txt),
[pre-lifetime green](issue-26-pre-lifetime-green-browser.txt).

Lifetime tests were added alone at `cd801fc4f25cac83be2dddd3b88b253fa56faf7e`.
[Run 39801085363, job 119901625254](https://github.com/porntaned/ERP-for-Factory/actions/runs/39801085363/job/119901625254)
reproduced the gap on PostgreSQL: **21 failed, 79 passed in 5.27s**. Ten parent
delete/PK-move cases and three same-statement direct-parent replacements did not raise
at statement time; eight Item/Plant fixed-snapshot cases lacked the required isolation
guard. The [browser record](issue-26-lifetime-red-browser.txt) captures the failed job;
the exact counts and case names were read from its GitHub raw job log. The raw log's
temporary signed storage URL is intentionally not reproduced here.

Final implementation commit `040b883c313cb70e05bdaef57839a4f07bcd3ee3`:
[Foundation run 39802033213](https://github.com/porntaned/ERP-for-Factory/actions/runs/39802033213),
[PostgreSQL job 119905052382](https://github.com/porntaned/ERP-for-Factory/actions/runs/39802033213/job/119905052382)
**succeeded**. The actual workflow used `postgres:18.6-bookworm`, applied migrations
to fresh PostgreSQL, checked Django/model-migration drift and Ruff, then ran:

| Command | Result |
| --- | --- |
| `uv run pytest -q tests/inventory/test_stock_ledger.py tests/inventory/test_stock_ledger_concurrency.py tests/inventory/test_stock_parent_lifetime.py --tb=short` | **121 passed in 7.23s** |
| `uv run pytest -q --tb=short` | **402 passed in 12.00s** |

The job also passed the retained deactivation, unsaved-user and event-identity
regressions. Final CI evidence belongs to the exact tested commit above; later
documentation commits do not change runtime behavior. No local PostgreSQL run is
claimed. [Independent source review](../reviews/issue-26-stock-ledger-independent-review.md)
is separate from root's CI inspection and self-verification.

## Manager self-Scrutinize and handoff

- **Intent:** enforce immutable, exact quantities and nonnegative pair balances for
  M4.1 while preserving the identity of every referenced history parent.
- **Trace:** model/field constraints, append trigger, Lot-first locks, parent guards,
  immediate direct FKs, balance query, and migration reverse/reapply were traced.
  Existing Quality lock order and Warehouse identity seams were checked.
- **Verify:** controlled RED, later lifetime RED and final PostgreSQL GREEN are linked
  above. The final suite covers invalid/empty/large quantities, Unicode reason,
  cross-organization inputs, concurrent writes, rollback, identity reuse and migration
  behavior. `git diff --check origin/main...HEAD` passed before this evidence update.
- **Report:** no remaining confirmed defect within M4.1's ordinary-write boundary.
  Per-pair SUM is linear in ledger history; posting authorization, Quality eligibility,
  idempotency, reversals, privileged DB administration and deployment remain outside
  this issue.
- **Verdict:** `ship` for an owner-review PR after the separate source review and
  exact-commit CI above. Owner acceptance and merge remain pending.

## Owner merge and main push CI

On 2026-10-23, root checked the live repository rather than relying on the chat
summary. [PR #27](https://github.com/porntaned/ERP-for-Factory/pull/27) was merged by
owner `porntaned` at **10:03 Asia/Bangkok**, merge commit
`a8c93fc461ab4115b69b4c5082f7f31e657ca865`. [Issue #26](https://github.com/porntaned/ERP-for-Factory/issues/26)
was closed as **completed** through that PR. Its five acceptance checkboxes and
stale pending-acceptance sentence were reconciled with linked evidence through the
GitHub browser UI; [saved issue screenshot](issue-26-completed.jpg).
The PR description's pending-acceptance sentence was also updated
([saved PR screenshot](issue-26-merged-pr.jpg)).

Local recovery commands (PowerShell, Windows):

```powershell
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
git fetch origin
git rev-parse origin/main
git switch -c codex/docs/m41-post-merge origin/main
git diff --exit-code 763ebcc1ee320a5623325a35e8630c34d99a523d HEAD
```

Initial branch was `codex/inventory/stock-ledger`, clean at
`763ebcc1ee320a5623325a35e8630c34d99a523d`; remote URL was
`https://github.com/porntaned/ERP-for-Factory.git`. The first sandboxed fetch could
not write `.git/FETCH_HEAD`; the approved retry succeeded, advancing `origin/main`
from `e806b64` to the merge SHA above. The documentation branch starts at that
merge. The final diff command exited 0 with no output: the merged tree matches the
PR head, so no M4.1 implementation was repeated.

The live Actions list showed [Foundation #96](https://github.com/porntaned/ERP-for-Factory/actions/runs/39892983263)
as the latest run at the start of reconciliation: **push / main / Success**.
[Job 120216811092](https://github.com/porntaned/ERP-for-Factory/actions/runs/39892983263/job/120216811092)
succeeded in 44s. Checkout log `git log -1 --format=%H` recorded the exact tested
merge SHA `a8c93fc461ab4115b69b4c5082f7f31e657ca865`.
Expanded runtime/connection logs recorded Python **3.14.8**, Django **5.2.18**,
psycopg **3.3.6**, `vendor=postgresql`, server
**18.6 (Debian 18.6-1.pgdg12+2)**. The workflow uses Ubuntu 24.04 and disposable
`postgres:18.6-bookworm`, not a local database.

| Observed CI command | Result on merge SHA |
| --- | --- |
| `uv run pytest -q tests/inventory/test_stock_ledger.py tests/inventory/test_stock_ledger_concurrency.py tests/inventory/test_stock_parent_lifetime.py --tb=short` | **121 passed in 5.99s** |
| `uv run pytest -q --tb=short` | **402 passed in 8.80s** |

The same successful job includes Django configuration, PostgreSQL connectivity,
model/migration drift, fresh migrations, Ruff and the retained deactivation,
unsaved-user and event-identity regressions. These are **observed CI results**;
no new local PostgreSQL execution or independent database verification is claimed.
The existing independent review remains a source review of `040b883`, not a review
of this documentation update or an independently executed database suite.

Status reconciliation changes README, TASKS and this evidence only, plus saved
issue/PR screenshots and an explicitly unapproved M4.2 proposal. M4 overall and
M4.2–M4.7 remain unchecked. No application code, tests, migrations, dependencies,
workflow, merge or deployment changed in this reconciliation.

### Documentation self-Scrutinize

- **Intent/smaller solution:** reconcile completed M4.1 with actual merge/CI evidence;
  update existing status surfaces and append this addendum, preserving the original
  independent review and historical handoff rather than rewriting their verdicts.
- **Trace:** PR #27's merge event → exact merge SHA → main-push run → job checkout,
  runtime/connection and targeted/full results → Issue closure and five acceptance
  checkboxes → README/TASKS links. Reviewed the M4.2 proposal against existing role
  enums, balance-query boundary and Quality's default HOLD/transition locks. Proposal
  decisions are explicitly unapproved; no new delivery is claimed.
- **Verification:** `git diff --check` passed. `.venv/Scripts/python.exe -` with an
  inline `pathlib`/`re` Markdown check passed: 4 edited/new Markdown files, 118 local
  link targets exist, fenced blocks balanced; M4.1 alone checked, M4 overall and
  M4.2–M4.7 unchecked. `git diff --name-only` and `git status --short` confirmed the
  documentation/image-only boundary. These checks ran on the uncommitted
  documentation tree based on `a8c93fc`; this is self-verification, not a fresh
  PostgreSQL run. The tested application SHA remains the merge SHA above.
- **Report/verdict:** `ship` for a documentation PR; no actionable mismatch remains
  in the changed status text. This is root's **self-review**, not independent review.
  Owner review and merge of the reconciliation remain pending. M4.2 needs a separate
  approved Issue, especially its HOLD receipt and receipt-only retry decisions.
