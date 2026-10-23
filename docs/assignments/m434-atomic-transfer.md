# M4.3.4 — Atomic same-Plant transfer

Repository: `porntaned/ERP-for-Factory`  
Branch: `codex/inventory/atomic-transfer`  
Base: `b4b44579352a490e1432783e1a34d571b6bf37ac`  
[Issue #36](https://github.com/porntaned/ERP-for-Factory/issues/36).
Status: implementation verified on PostgreSQL; ready for owner review. No merge authorized.

## Verified baseline and boundaries

Working tree was clean; origin/main fetched at the base above. PR #35 is merged,
Issue #34 completed and [main CI #116](https://github.com/porntaned/ERP-for-Factory/actions/runs/39976575083)
passed. No existing implementation of a stock transfer command was found.

[Quality gate](../../inventory/transfer_policy.py) requires a caller atomic transaction
and PostgreSQL READ COMMITTED; it locks the persisted Lot, Item, both Warehouses in ID
order and their Plant. Source must be RELEASED; destination disposition remains unchanged.
[Ledger migration](../../inventory/migrations/0002_stock_ledger.py) locks the Lot before
checking current persisted balance and rejects a negative balance at the database boundary.

## Intended behavior

One existing Lot, two distinct Warehouses in one Plant and matching Organization,
positive exact finite base-UOM Decimal below 10^14, representable at six fractional
places, and a nonblank Unicode reason preserved exactly.

Within one atomic block/savepoint:

1. Validate input without rounding, including trailing-zero acceptance.
2. Acquire the existing Quality/identity locks in their established order.
3. Lock and check the persisted active actor and WAREHOUSE grants at both ends.
4. Read source stock under the Lot lock; reject insufficient stock.
5. Append source debit and destination credit for the exact same amount/actor/reason.
6. Commit both or roll both back, including when the caller catches an exception
   inside its own outer transaction. Use Decimal.copy_negate for exact sign reversal
   independent of the caller Decimal context.

Return both immutable ledger entries. No transfer model, permanent pair association,
request ID, duplicate retry handling, endpoint, UI or deployment is proposed here.
Those interfaces must not imply idempotency; uncertain retries need M4.3.6 first.

## Owner-selected authorization prerequisite

Owner explicitly approved including minimal M4.3.2 enforcement here: a persisted
active actor with a WAREHOUSE grant at BOTH warehouses, locked through posting.
No role is granted automatically. QUALITY/staff/superuser status alone cannot bypass
these grants. Current persisted deactivation/revocation must win if committed first.

## Acceptance test plan

- Exact debit/credit, total conservation, empty/default-HOLD destination unchanged.
- Entire source balance transferable; insufficient or empty stock leaves both unchanged.
- Invalid amount/type/precision/reason and same/cross-Plant identities rejected.
- Small Decimal context must not round the debit.
- Inject an actual PostgreSQL destination rejection: debit must roll back too, even
  with an outer transaction catching the database error and continuing unrelated work.
- Two transfers competing for stock serialize and cannot overdraw.
- Concurrent Quality HOLD and parent changes are checked inside the posting transaction.
- Missing/wrong/revoked grants and persisted deactivation reject without writes.
- Targeted PostgreSQL tests first, then existing Inventory/Quality and full regressions.

PostgreSQL results are recorded below; completion awaits owner acceptance. Root implemented and self-reviewed
this slice; no independent agent review is claimed. Owner approval for PR #35 does not
authorize merging this work.

## Implementation trace and self-Scrutinize

[Internal command](../../inventory/transfers.py): `transfer_stock` validates quantity
and reason, opens an atomic block/savepoint, invokes the existing Quality gate in that
same transaction, locks current actor then exact grants ordered by Warehouse ID,
checks source balance, and writes the negative/positive ledger entries. `copy_negate`
avoids Decimal-context rounding. Any error escapes the atomic block, rolling both back.
Database nonnegative/identity/immutability triggers remain unchanged as the final guard.

[Tests](../../tests/inventory/test_atomic_transfer.py) exercise the actual command and
use a test-only PostgreSQL credit-rejection trigger for partial-write rollback. Race tests
reuse the observed `pg_blocking_pids` helper, not timing-only assertions. The new workflow
step runs targeted tests before the existing full regression suite.

Smaller alternative considered: two ledger writes without a shared transaction would
lose stock if the credit failed. Separate permission/Quality preflight would race with
revocation/HOLD. Both checks belong inside the same posting transaction.

Exclusions: typed transfer record/persistent pairing, request retry/deduplication, HTTP/API,
UI, schema changes, dependencies, real data, reversal, valuation and deployment. Actor,
reason and database time exist on each ledger row, but M4.3.5 is not complete.
Each repeated invocation is a new transfer; no auto-retry or retry-safe claim is made.
Full M4.3.7 independent review remains pending. Self-review verdict: **ship** for
this bounded command, because exact atomicity, rollback and serialized eligibility passed
on PostgreSQL. A repeated invocation still posts again by design; no endpoint is exposed.

## Local checks

Windows PowerShell with `.venv/Scripts/python.exe`: `-m ruff check .` PASS; Ruff format check of both new Python files PASS;
Markdown links/fences: 2 files / 112 local targets PASS; `git diff --check` PASS. `.env` absent; use disposable CI PostgreSQL 18.6,
not SQLite/mocks, to verify business/locking behavior. No local database result claimed.

## PostgreSQL verification — 2026-10-23

Application SHA: `99f96d7c7a0b266400e53a3bc12847ffa8774312`.
[Foundation #117 / job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39979297426/job/120502035171)
completed successfully. Environment: ubuntu-24.04, `vendor=postgresql`, server
**18.6 (Debian 18.6-1.pgdg12+2)**. Python/Django/psycopg use the existing exact workflow
pins. Fresh migrations, model/migration-state check, Django check and Ruff passed.

| Actual command | Observed result |
| --- | --- |
| `uv run pytest -q tests/inventory/test_atomic_transfer.py --tb=short` | **66 passed in 2.72s** |
| `uv run pytest -q --tb=short` | **591 passed in 19.22s** |

The real PostgreSQL destination-rejection trigger raised IntegrityError after the
source insert. The command savepoint rolled the debit back; the caller transaction
could still write an unrelated Organization. The trigger was test-only and removed.
Source depletion and 9 actual lock-wait cases passed, including 8 Quality/authorization
mutation orderings and 1 competing transfer. Existing Quality gate and receipt/ledger
regressions also passed in the full suite.

Evidence is self-verification, not independent review. Final documentation-only commit
must pass CI too before merging. M4.3.5/M4.3.6 and full M4.3.7 remain incomplete.
