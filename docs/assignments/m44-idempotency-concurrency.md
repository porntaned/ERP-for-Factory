# M4.4 — request idempotency and concurrency audit

Repository: `porntaned/ERP-for-Factory`; branch: `codex/inventory/m44-idempotency-concurrency`.
[Issue #48](https://github.com/porntaned/ERP-for-Factory/issues/48). Base:
`e29266d07740eec89fa1a6608cb75d661e1b8ea4`. Owner approved the scope below on 2026-10-30.
No merge or deployment was authorized.

## Scope and exclusions

Audit three candidate gaps, add PostgreSQL tests only for gaps confirmed real, change
application code only if a test proves a defect. Excluded: reversal (M4.5), UI/API (M4.6),
demo (M4.7), any new policy without owner approval, stock adjustments, real data,
dependencies, merge, deployment.

## Findings

| Candidate gap | Result | Evidence |
| --- | --- | --- |
| Receipt vs transfer racing on one Lot-Warehouse pair | **Real coverage gap, no defect.** Existing code already serializes correctly. Added 3 tests. | `tests/inventory/test_receipt_transfer_serialization.py` |
| Same UUID reused across commands | **Behavior confirmed; policy decision for the owner.** Not changed. | probe below |
| Retry after ambiguous failure | **Already covered.** No new test. | `test_transfer_requests.py`, `test_stock_receipt_concurrency.py` |

### 1. Receipt and transfer serialization

The existing suites cover receipt vs Quality, transfer vs Quality/authorization, competing
transfers and competing receipts, but no test combined a receipt and a transfer on the same
pair. Added, with lock waits observed through `pg_blocking_pids`, not timing:

- a transfer of 150 against a balance of 100.000001 waits for a concurrent receipt of 60 and
  succeeds only after it commits (final balances 10.000001 / 150);
- the same transfer waits for a receipt that is rolled back and is then rejected as
  insufficient, leaving no receipt, transfer or extra ledger rows;
- a receipt waiting behind a committed transfer posts without altering that transfer.

The receipt and transfer use **different actors**. A first draft used one actor and still passed
with the transfer's Lot lock disabled, because both commands lock the same User and grant rows
and therefore serialize on authorization alone. That draft would not have proved Lot-level
serialization, so it was replaced.

Non-vacuity check (local, temporary, reverted): changing `locked_lot` in
`inventory/transfer_policy.py` from `select_for_update()` to a plain query made 2 of the 3 tests
fail with "concurrent writer did not reach an observed PostgreSQL lock wait"; the third, which
exercises the receipt side, still passed as expected. The file was restored with `git checkout`.
There was no RED phase against production code because the behavior was already correct; these
are regression tests, not a fix.

### 2. Cross-command request keys — owner decision needed

`StockReceipt.request_id`, `StockTransfer.request_id` and `LotDispositionEvent.request_id` are
three independent unique columns and each command looks up only its own table. A temporary,
uncommitted probe on a synthetic scope used one UUID for `receive_stock`, `transfer_stock` and
`transition_lot_disposition`; all three succeeded, leaving one row per table with that key.

This matches the documented per-command contracts, so it is not shown to be a defect. Rejecting
reuse across commands would need a new cross-table rule (shared key registry or trigger) and a
schema change. Options for the owner: (a) keep per-command keys and document that, (b) add a
shared key registry in a separate approved issue. No change is made here.

### 3. Retry after ambiguous failure

Exact replay returns the original rows without a second movement, replay re-checks current
authorization, an injected history-insert failure and an outer rollback leave nothing behind and
the same key can retry, and cross-Lot UUID races roll back the losing entries. The only
uncovered sub-case is a backend terminated exactly between the debit and credit inserts, which
cannot be triggered deterministically without fault-injection hooks; not attempted.

## Environment and verification

- Local development only: Python 3.14.6 (project pins 3.14.8; unavailable from uv in the
  session), PostgreSQL **16.15**, not the project's 18.6. Not used as evidence of record.
- Local results at the tested working tree: new file 3 passed, repeated 3 times; Ruff and
  `makemigrations --check` clean; full suite 647 passed in 43.29s.
- CI: [Foundation #145](https://github.com/porntaned/ERP-for-Factory/actions/runs/41035056998)
  on tested SHA `06b88aa8e888dc9cd66303aba6c04c91e3dfb737` completed **success**; job steps
  `Run receipt and transfer serialization tests` and `Run ERP tests` each concluded success.
  The workflow's disposable service is PostgreSQL 18.6. Limit: the session could read step
  conclusions through the GitHub API but could not download log text, so test counts and the
  server version line were **not** read from this run and are not claimed here.
- Commits after the tested SHA change documentation only.

## Review status

Self-review only so far. No independent review is claimed. M4.4 stays **unchecked** in
`docs/TASKS.md`: only one of three candidate items produced new tests, and the cross-command
key question awaits the owner.
