# Issue #26 — stock ledger verification

Repository `porntaned/ERP-for-Factory`; [Issue #26](https://github.com/porntaned/ERP-for-Factory/issues/26).
[Contract/assignment](../assignments/issue-26-stock-ledger.md).

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
