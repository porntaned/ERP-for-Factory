# Issue #29 — independent final Scrutinize

- Reviewer: separate agent `/root/m42_final_review`; source review only.
- Repository: `porntaned/ERP-for-Factory`.
- Branch: `codex/inventory/synthetic-receipt`.
- Reviewed head: `0a96eda80107f088d043c0ed47683ae6e6ddbd69`.
- Base: `21ab14082fb18a99bfa1fb1c3a5061323bfadc33`.
- Scope: committed application, migration, tests and CI changes for owner-approved M4.2. Uncommitted handoff documentation was outside the runtime review.

## Intent and simpler alternative

Receive synthetic stock into an existing Lot/Warehouse with persisted destination authorization, unchanged Quality disposition and receipt-only UUID idempotency. The implemented normalized receipt linkage reuses the immutable ledger payload rather than introducing duplicate mutable receipt payload; no smaller change identified that satisfies these boundaries.

## Traced paths

- `inventory/services.py:50`: saved-record checks, finite positive Decimal below the range limit, exact precision with trailing zeros allowed, nonblank exact reason and UUID validation.
- `inventory/services.py:73`: READ COMMITTED requirement; persisted Lot UPDATE followed by Item, Warehouse and Plant SHARE locks. Caller-cached parent relations do not decide organization eligibility.
- `inventory/services.py:124`: persisted active User and exact destination WAREHOUSE grant UPDATE locks precede posting and retry lookup; no superuser or other-role bypass.
- `inventory/services.py:106`: identical UUID/payload resolves the original receipt; changed actor, Lot, Warehouse, quantity or reason conflicts.
- `inventory/services.py:154`: nested savepoint contains ledger append and receipt creation. A global UUID collision across Lots rolls back the losing ledger before resolving the winner.
- `inventory/models.py:59` and `inventory/migrations/0004_stock_receipt.py:35`: protected one-to-one linkage, unique UUID, existing positive ledger validation, GENERATED ALWAYS identity and immutable receipt trigger; followed existing ledger append, immutability and parent lifetime guards in migrations 0002/0003.
- Existing `quality/services.py`: shared Lot lock coordinates transitions; receipt code writes no Quality event and preserves default HOLD, explicit HOLD and RELEASED.
- `tests/inventory/test_stock_receipt.py`: invalid/stale identities and authorization, retry conflicts, exact quantity boundaries, outer rollback, injected failure after the real ledger insert, raw SQL constraints, protected linkage and migration reverse/reapply.
- `tests/inventory/test_stock_receipt_concurrency.py`: observed PostgreSQL lock waits for same-key retries, cross-Lot UUID collision with a separate actor, authorization mutations, Quality transitions and parent identity mutations.

## Findings and evidence limits

No actionable defects found in the reviewed source and test design. Review was read-only until this report was requested. The reviewer did not execute tests, access PostgreSQL, inspect live CI or change application files.

The manager independently observed [CI run 39909020029, job 120267442017](https://github.com/porntaned/ERP-for-Factory/actions/runs/39909020029/job/120267442017) at the reviewed SHA: PostgreSQL 18.6, Python 3.14.8, Django 5.2.18, psycopg 3.3.6; 87 targeted tests passed in 3.86 seconds and 489 full-suite tests passed in 17.32 seconds. These are manager-observed execution results, not execution by this reviewer.

Ordinary application and SQL storage boundaries were reviewed; privileged database override, trigger disabling and TRUNCATE are excluded. Direct storage writes do not establish business authorization. This review is not evidence of deployment, transfer support or full M4.4 concurrency/idempotency completion.

## Verdict

**ship** — receipt intent and stock movement share one rollback boundary while retaining one authoritative immutable payload; persisted authorization is rechecked even for retries. Owner review and merge remain required.
