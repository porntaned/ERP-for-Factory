# M4.5 — reversal of receipts and transfers

Repository `porntaned/ERP-for-Factory`; branch `codex/inventory/m45-reversal`; base `main`
`28d8d30bd3f4871a3f44f2ed78c98dd5eaf1d256`. [Issue #59](https://github.com/porntaned/ERP-for-Factory/issues/59). Owner approved scope
and policy on 2026-11-04. No merge or deployment authorized by this work.

## Owner policy

1. Reverse receipts and transfers with new compensating entries that reference the original;
   the original is untouched.
2. Active APPROVER at every warehouse involved; no rule that the actor differ from the original.
3. Whole transaction only.
4. Once only; a reversal cannot be reversed; insufficient stock is rejected, no cascade.
5. Receipt reversal in any Quality state; transfer reversal requires the original destination
   (where goods leave) to be RELEASED; Quality never changes.

Defaults not objected to: nonblank reason, UUID request with exact replay / changed-payload
conflict / current authority on replay, `REVERSAL` in the shared key registry, no time limit,
internal command only. A reversal corrects a mis-recorded document; it is not a supplier return.

## Delivered

- `inventory.StockReversal` (one-to-one to receipt or transfer, debit entry, credit entry for
  transfers) and migration 0009: link validation trigger (exact quantities, lot, warehouses,
  actor/reason pairing), immutability, registry trigger last, reversal entries cannot be adopted
  by receipts or transfers, unapplying refused while reversals exist (table locked first).
- `inventory/reversals.py`: `reverse_receipt`, `reverse_transfer`; lock order Lot → Item →
  Warehouses → Plant → actor → APPROVER grants → registry, as the other commands.
- Admin lists `StockReversal` read-only. CI step for `test_stock_reversal.py`.

## RED / GREEN

All 32 initial tests failed with the controlled fixture message "M4.5 reversal contract absent"
before the model and command existed; then GREEN. After independent review, 12 more tests
(transfer-link field cases, transfer replay/once-only, inactive approver, cross-Lot same-UUID
race, race with a destination HOLD) passed against the repaired code.

Mutation checks (each reverted): removing the reversal link trigger, the adoption triggers, the
receipt-branch warehouse check, each transfer-branch credit warehouse / credit lot / actor /
reason check, or the receipt command's `except IntegrityError` branch each made exactly the
intended test fail.

## Verification (local, development only)

PostgreSQL 16.15, Python 3.14.6 (project pins 18.6 / 3.14.8). Full suite 728 passed; Ruff,
`makemigrations --check` clean. Fresh DB: `migrate`, `seed_demo`, a real `reverse_receipt`
(−100), unapply refused while the reversal exists (tested), unapply/reapply with none: OK.
CI on PostgreSQL 18.6 is recorded in the PR (step conclusions only).

## Review

Independent read-only review: [m45-reversal-independent-review.md](../reviews/m45-reversal-independent-review.md),
verdict fix-then-ship; findings repaired and self-verified, not re-reviewed.
