# M4.3.5 — Immutable transfer history

[Issue #38](https://github.com/porntaned/ERP-for-Factory/issues/38)  
Repository: `porntaned/ERP-for-Factory`  
Branch: `codex/inventory/transfer-history`  
Base: `0df0923b293a889dc2ca5316062d5350f7e60a9a`  
Status: implemented; PostgreSQL verification pending; not merged.

## Scope and baseline

Owner requested M4.3.5 only: persistent transfer identity linking both ledger entries,
with actor, reason, time and traceability. Working tree was clean before work. Fetched
origin/main matched the base; PR #37 merged, Issue #36 completed and
[main Foundation #120](https://github.com/porntaned/ERP-for-Factory/actions/runs/39980301308)
passed. GitHub had no open issues before creating #38.

No request UUID, retry deduplication, reversal, UI/endpoint, permission/Quality policy
change, real data, deployment or merge is authorized here. M4.3.6 and full M4.3.7 remain
pending. Existing history is retained without guessing missing transfer pairs.

## Implementation trace

- [Model](../../inventory/models.py): StockTransfer has protected unique source and
  destination ledger links and a database-authored created_at. The existing ledger rows
  own actor, Lot, Warehouse, signed exact quantity, preserved reason and ledger time.
  No duplicate payload fields can drift from the ledger.
- [Migration](../../inventory/migrations/0005_stock_transfer.py): identity GENERATED
  ALWAYS, immutable UPDATE/DELETE guard, signed equal-and-opposite entries, same Lot,
  actor and reason, distinct Warehouses in the same Plant. Missing rows cannot be
  forward-referenced. Unique links prevent reuse and provide indexed lookups.
- Receipt and transfer ownership are mutually exclusive. Both insertion paths lock
  ledger rows (ascending ID for a pair) and then read the current ownership at READ
  COMMITTED. A receipt cannot be reclassified as a transfer or vice versa, even in a race.
- [Command](../../inventory/transfers.py): link creation occurs after both ledger inserts
  in the SAME atomic block/savepoint. Failure rolls all three writes back. The returned
  `(debit, credit)` tuple stays compatible; `debit.transfer_out` and `credit.transfer_in`
  resolve the same StockTransfer identity.
- New transfers receive history automatically. Migration creates no inferred pairs for
  pre-existing unlinked ledger rows. It preserves existing receipts and ledger payloads.

## Verification plan / self-Scrutinize

[Tests](../../tests/inventory/test_transfer_history.py) trace command/model/actual SQL:
valid history and reverse relations, mismatched payload/roles/parents, missing rows,
unique entry ownership, immutable history and protected ledger references, forged ID/time,
real database history-insert failure and caller recovery, receipt/transfer insertion
orders and observed PostgreSQL lock waits, stale isolation rejection, migration upgrade
preserving pre-existing unlinked ledger and receipts. Existing atomic transfer, Quality,
receipt and full regressions must still pass.

Smaller alternative considered: storing two IDs only in the response loses durable
traceability. Duplicating actor/reason/amount would create inconsistent copies. A typed
record with two protected unique links is the smallest durable history; SQL checks are
needed because application validation alone does not protect direct storage paths.

Scope stays bounded: not a transfer request/idempotency model. Repeated command calls
create new transfers. No auto-retry or endpoint is added. Source Quality and both-end
WAREHOUSE authority remain as approved in M4.3.3/M4.3.4.

Root implemented, traced and self-reviewed this slice. No independent agent review is
claimed. Verdict pending PostgreSQL verification. The Postgres best-practices skill
informed indexed foreign keys and consistent lock ordering; no Supabase service is used.

## Local checks

Windows PowerShell / `.venv/Scripts/python.exe`: Ruff check and format of changed Python
files PASS. No local PostgreSQL claim: `.env` is absent; use disposable CI PostgreSQL.
Exact CI SHA, actual commands, test results and limitations will be recorded after running.
