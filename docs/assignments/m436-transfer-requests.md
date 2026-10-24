# M4.3.6 — UUID transfer requests

[Issue #42](https://github.com/porntaned/ERP-for-Factory/issues/42) ·
Repository `porntaned/ERP-for-Factory`, branch `codex/inventory/transfer-idempotency`.
Base: `3d876cc129f9f889b636926b40798423a53d31f1`.
Status: implemented, PostgreSQL verification pending; no merge/deployment authorized.

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
loop is introduced. Verdict awaits PostgreSQL results and owner acceptance.

Local environment: Windows PowerShell; `.env` absent during preceding work, so PostgreSQL
claims require disposable CI PostgreSQL 18.6. Ruff/format and Markdown/diff checks are
recorded with the actual tested SHA in the PR; no SQLite/mocks/local DB result claimed.
