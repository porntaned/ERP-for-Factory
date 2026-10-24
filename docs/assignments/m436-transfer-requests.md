# M4.3.6 — UUID transfer requests

[Issue #42](https://github.com/porntaned/ERP-for-Factory/issues/42) ·
Repository `porntaned/ERP-for-Factory`, branch `codex/inventory/transfer-idempotency`.
Base: `3d876cc129f9f889b636926b40798423a53d31f1`.
Status: owner-authorized [PR #43](https://github.com/porntaned/ERP-for-Factory/pull/43) merged at `e8ad707b86f7c613c3db291fd6dcabd3f491a569`; [Issue #42](https://github.com/porntaned/ERP-for-Factory/issues/42) closed completed; [main CI #132](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067226064) passed. No deployment.

## Verified scope — 2026-10-24

Git working tree initially clean; origin/main fetched at the base above. PR #39 merged;
main CI #126 passed. PR #41 remains open (docs only, checks passed); it was not merged
or included in this branch. Only Issue #40 was open before creating #42.

Owner explicitly selected: new commands require UUID request_id; exact retry returns
original entries, changed payload conflicts; legacy rows retain NULL without inferred
keys. Exact retry may return history after source becomes HOLD, but STILL requires
current persisted active actor and WAREHOUSE grants at both ends. New stock movement
requires RELEASED source. These rules do not grant roles or change Quality disposition.

## Trace and constraints

- [Model](../../inventory/models.py) / [migration 0006](../../inventory/migrations/0006_transfer_request_id.py):
  nullable unique UUID on StockTransfer, no default/backfill. Existing rows stay NULL;
  NULL is storage compatibility for legacy/unkeyed internal records, not a valid command
  request. The existing immutable trigger also forbids changing/assigning a request ID.
- [Transfer command](../../inventory/transfers.py): validate UUID and payload; lock
  current persisted scope; lock/check active actor and both grants; read existing UUID;
  return identical original pair or raise TransferConflictError. Payload identity includes
  Lot, source/destination, actor, exact quantity and preserved reason. Decimal trailing
  zeros are equivalent; strings are not normalized.
- Only a new UUID checks current source Quality and available quantity, then appends both
  ledger rows and history. Nested savepoint rolls back ALL losing writes if a different-Lot
  UUID race reaches unique insertion; read the committed winner after rollback. Unrelated
  IntegrityError with no winning UUID is re-raised, never silently treated as replay.
- [Quality scope](../../inventory/transfer_policy.py): extract persisted identity locking
  into lock_transfer_scope; require_transfer_quality remains the RELEASED gate for callers.
  Shared locks retain established Lot/Item/Warehouse/Plant order and READ COMMITTED.
- Return contract stays (debit, credit). request_id is a new REQUIRED keyword argument;
  existing internal test caller now passes uuid4 per new command. There is no endpoint/UI.
- [Request tests](../../tests/inventory/test_transfer_requests.py): replay, conflict,
  current authorization, HOLD/exhausted source replay, DB uniqueness/immutability,
  rollback/retry, observed same-key/cross-Lot waits and legacy upgrade. Existing 0005
  migration test uses historical model state and restores latest migrations, so it still
  tests 0005 rather than accidentally using a future field absent in that schema.

## Self-Scrutinize and exclusions

Root implemented and self-reviewed; no independent agent review claimed. Smaller
alternative (lookup before writes only) fails concurrent UUID races; a unique database
key plus losing-write rollback is required. The old receipt pattern informs the same
savepoint boundary, without mixing receipt and transfer UUID namespaces.

No new dependency, real data, permissions/Quality policy change, reversal, HTTP/UI,
M4.4 completion or M4.3.7 independent review. Do not redo already-green atomic transfer
and Quality work; run their regressions after targeted request tests. No automatic retry
loop is introduced. Self-review verdict: **ship** for this bounded request contract; exact replay,
conflicts, current authorization, losing-write rollback and legacy migration passed.
The original pre-merge self-review above is historical; owner acceptance and merge are now recorded in the status above.

Local environment: Windows PowerShell; `.env` absent during preceding work, so PostgreSQL
claims require disposable CI PostgreSQL 18.6. Ruff/format and Markdown/diff checks are
recorded with the actual tested SHA in the PR; no SQLite/mocks/local DB result claimed.

## PostgreSQL evidence — 2026-10-24

Tested application/test SHA: `1cddc7a461bb7a51cf84e1841db225f12b77e6c6`.
[Foundation #129 / job](https://github.com/porntaned/ERP-for-Factory/actions/runs/40066789351/job/120791629207)
completed successfully on ubuntu-24.04, vendor=postgresql,
server **18.6 (Debian 18.6-1.pgdg12+2)**. Fresh migrations, model/migration-state
check, Django check and Ruff passed, using the existing pinned Python/Django/psycopg.

| Actual command | Observed result |
| --- | --- |
| `uv run pytest -q tests/inventory/test_transfer_requests.py --tb=short` | **22 passed in 1.67s** |
| `uv run pytest -q --tb=short` | **642 passed in 24.01s** |

Three observed PostgreSQL lock-wait cases covered same-key exact/conflicting requests
and different-Lot global UUID contention. The cross-Lot loser retained its original
balance and created no orphan ledger/history. Upgrade kept two legacy NULL IDs intact.
Original atomic transfer, history/receipt ownership and Quality regressions also passed.
Local Ruff check/format, Markdown links/fences (2 files / 117 local targets), and
`git diff --check` passed; no local PostgreSQL result is claimed.

Final pre-merge documentation CI passed: [push #130](https://github.com/porntaned/ERP-for-Factory/actions/runs/40066962008) and [PR #131](https://github.com/porntaned/ERP-for-Factory/actions/runs/40066999089), head `95cf55a831613db5fd6252b73fef9ccf4e9cb315`.
Owner merge and main CI are linked above. M4.3.7 independent review is tracked separately in [readiness](m437-transfer-readiness.md). Reversing migration 0006 drops request IDs and deduplication;
no schema rollback/deployment is authorized by this work. PR #41 remains separate/open.
