# M4.3.5 — Immutable transfer history

[Issue #38](https://github.com/porntaned/ERP-for-Factory/issues/38)  
Repository: `porntaned/ERP-for-Factory`  
Branch: `codex/inventory/transfer-history`  
Base: `0df0923b293a889dc2ca5316062d5350f7e60a9a`  
Status: owner-authorized PR #39 merged; Issue #38 completed; main CI passed.
See the dated post-merge addendum below; earlier scope/verification text records pre-merge work.

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
claimed. Verdict: **ship** for this bounded history slice, because pair integrity,
immutability, atomic rollback, ownership races and upgrade preservation passed on PostgreSQL. The Postgres best-practices skill
informed indexed foreign keys and consistent lock ordering; no Supabase service is used.

## Local checks

Windows PowerShell / `.venv/Scripts/python.exe`: Ruff check and format of changed Python
files PASS. No local PostgreSQL claim: `.env` is absent; use disposable CI PostgreSQL.
Local Markdown: 2 files / 114 local targets, fences and pending acceptance gates PASS;
`git diff --check` PASS.

## PostgreSQL evidence — 2026-10-23

Tested application/test SHA: `fb3de5ea7a60b41a38036b92d2e0c4c3980090c5`.
[Foundation #123 / job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39981798189/job/120510693093)
completed successfully on ubuntu-24.04 with `vendor=postgresql` and server
**18.6 (Debian 18.6-1.pgdg12+2)**. Python/Django/psycopg use the existing exact workflow
pins. Fresh migration, model/migration-state check, Django check and Ruff passed.

| Actual command | Observed result |
| --- | --- |
| `uv run pytest -q tests/inventory/test_transfer_history.py --tb=short` | **29 passed in 1.67s** |
| `uv run pytest -q --tb=short` | **620 passed in 22.54s** |

The targeted suite includes a real PostgreSQL history rejection after ledger inserts,
3 observed lock-wait races (two receipt/transfer orders and duplicate pair), immutable
history/identity guards, and a 0004-to-0005 upgrade that retains old ledger and receipt
rows without creating inferred transfers. Existing 66 atomic transfer tests and Quality,
receipt, ledger regressions remain green in the full suite.

Repair evidence: [Foundation #122](https://github.com/porntaned/ERP-for-Factory/actions/runs/39981565900)
had 1 failed / 28 passed: the identity UPDATE guard correctly raised ProgrammingError
(`column id can only be updated to DEFAULT`) while the test expected IntegrityError.
The final test checks the actual database exception/message; history constraints were
not weakened. The explicit identity INSERT assertion also checks GENERATED ALWAYS.

No independent review is claimed; full M4.3.7 remains pending. A final documentation-only
commit must pass CI before merge. Owner acceptance/merge and deployment are not inferred.

## Owner-authorized merge and handoff — 2026-10-23

Owner explicitly approved [PR #39](https://github.com/porntaned/ERP-for-Factory/pull/39).
Merge commit: `3d876cc129f9f889b636926b40798423a53d31f1`; [Issue #38](https://github.com/porntaned/ERP-for-Factory/issues/38)
closed completed. [Main CI #126](https://github.com/porntaned/ERP-for-Factory/actions/runs/39983366988)
passed after merge (1m 21s). Git fetch and GitHub browser independently confirmed main.
No deployment or M4.3.6 start occurred. This does not turn self-review into independent review.

[Project handoff](../handoff/PROJECT-STATUS-2026-10-23.md) and
[AI chat starter](../handoff/AI-CHAT-STARTER.md) preserve approved policies and remaining work.
