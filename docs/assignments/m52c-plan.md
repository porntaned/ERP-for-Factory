# M5.2c Implementation Plan

> **For agentic workers:** executed inline by one agent with `superpowers:executing-plans` and
> `superpowers:test-driven-development` (owner: solo, no sub-agents, self-review). Steps use
> checkbox (`- [ ]`) syntax.

**Goal:** reverse CONSUME/SCRAP/OUTPUT postings, require a shortfall reason on close, and name
held Lots in cancel/close refusals.

**Architecture:** Inventory owns a new `ProductionPostingReversal` (one opposite ledger entry per
posting) and the command that posts it; Manufacturing locks the order, enforces OPEN, and counts
reversals in holdings, net output and genealogy. PostgreSQL triggers re-check every rule.

**Tech Stack:** Django 5.2, PostgreSQL triggers in `RunSQL` migrations, pytest-django.

**Spec:** [`m52c-production-reversal.md`](m52c-production-reversal.md)

## Global Constraints

- Lock order: order row → Lot → Item → Warehouse → Plant → actor → grants.
- Request key command `POSTING_REV` (fits `max_length=12`).
- Reversal authority: active APPROVER at the posting's warehouse.
- Reversal only while the order is OPEN; once per posting; whole posting.
- OUTPUT reversible only if every entry of its Lot is an OUTPUT posting or the reversal of one.
- `shortfall_reason` nonblank iff net output < order quantity at close; null unless CLOSED.
- Every migration reversible; 0014 unapply refused while reversals exist.
- Tests run on PostgreSQL: `uv run --env-file .env pytest`.

## Review Focus

1. A raw SQL reversal (bypassing commands) on a CLOSED order or a used output Lot → rejected
   (Task 1/2 DB tests).
2. Two APPROVERs reverse the same posting at once → one reversal, the other `AlreadyReversedError`
   (Task 2 concurrency).
3. Close racing a CONSUME reversal → close refused (holding back) or reversal refused (CLOSED)
   (Task 2 concurrency).
4. OUTPUT reversal racing a transfer of the output Lot → exactly one succeeds (Task 2).
5. A quantity like `40.000000` in a refusal message → printed as `40` (Task 3).

---

### Task 1: Inventory reversal model, rules and command

**Files:** Modify `inventory/models.py`, `inventory/production.py`. Create
`inventory/migrations/0013_production_posting_reversal.py` (model + `POSTING_REV` choice),
`inventory/migrations/0014_production_posting_reversal_rules.py`. Test
`tests/manufacturing/test_production_reversal.py`.

**Interfaces — produces:**
- `inventory.models.ProductionPostingReversal(request_id, posting→ProductionPosting related_name="reversal", ledger_entry→StockLedgerEntry related_name="production_reversal", created_at)`
- `inventory.production.reverse_production_posting(*, posting, actor, reason, request_id) -> ProductionPostingReversal`
- `inventory.production.OutputLotUsedError`; `AlreadyReversedError` re-exported from `inventory.reversals`.

- [ ] Step 1: tests (call Inventory directly on postings made by `consume`/`scrap`/`output`
  helpers from `test_production_postings.py`):
  `test_inventory_reverses_each_kind_with_one_opposite_entry` (CONSUME credit at LINE-1, OUTPUT
  debit at FG, original entry unchanged, `posting.reversal` set),
  `test_inventory_reversal_needs_approver_at_the_posting_warehouse`,
  `test_inventory_reversal_replay_conflict_and_once_only` (same key → same row; other posting
  with same key → `PostingConflictError`; second key → `AlreadyReversedError`; consume key reused
  → conflict; registry row `POSTING_REV`),
  `test_output_reversal_refused_after_the_lot_moved` (transfer FG→RM-A and back → `OutputLotUsedError`),
  `test_output_reversal_allowed_after_release`,
  `test_database_checks_reversal_links` (raw insert: wrong quantity, wrong lot, receipt entry,
  posting entry → `IntegrityError`; update/delete of a reversal → `IntegrityError`; raw
  `StockReceipt`/`ProductionPosting` adopting a reversal entry → `IntegrityError`; raw OUTPUT
  reversal after a transfer → `IntegrityError`).
- [ ] Step 2: run, expect collection error (`ProductionPostingReversal` missing).
- [ ] Step 3: model + 0013 (makemigrations), 0014 triggers (link check, used-Lot check,
  immutability via `inventory_reject_stock_rewrite`, adoption triggers on receipt/transfer/
  stockreversal/productionposting, `inventory_register_request_key('POSTING_REV')` last,
  reverse SQL refusing while rows exist); command following `post_production_posting` locks.
- [ ] Step 4: run, expect pass; full `tests/inventory` still pass.
- [ ] Step 5: commit.

### Task 2: Manufacturing reversal command, totals and genealogy

**Files:** Modify `manufacturing/services.py`, `manufacturing/genealogy.py`. Create
`manufacturing/migrations/0007_posting_reversal_rules.py`. Test same file.

**Interfaces — produces:** `manufacturing.services.reverse_order_posting(*, order_posting, actor, reason, request_id) -> ProductionPostingReversal`.

- [ ] Step 1: tests:
  `test_reversed_consumption_returns_to_the_order_holding` (consume 30, reverse → line 40,
  `give_back(40)` succeeds), same for scrap,
  `test_reversed_output_lowers_net_output` (output 10, reverse, output 10 again into the same
  code succeeds; 11th unit refused),
  `test_reversal_refused_on_a_closed_order` (command → `MaterialValidationError`; raw insert →
  `IntegrityError`),
  `test_genealogy_nets_reversals` (fully reversed consumption drops from `inputs_of`; fully
  reversed output Lot drops from `outputs_of`),
  concurrency with `blocked_action`: `test_concurrent_reversals_of_one_posting`,
  `test_close_racing_a_consumption_reversal`, `test_output_reversal_racing_a_transfer`.
- [ ] Step 2: run, expect `ImportError` on `reverse_order_posting`.
- [ ] Step 3: 0007: `manufacturing_order_lot_holding` and output total add reversal entries; output
  ownership accepts own reversal entries; insert trigger on `inventory_productionpostingreversal`
  locks the order and requires OPEN. Python: `_order_holdings`, `_output_total`, genealogy
  `_per_order_lot` add `posting__reversal__ledger_entry__quantity_delta` (Coalesce 0) and drop
  zero rows; `reverse_order_posting` as spec.
- [ ] Step 4: run, expect pass; `tests/manufacturing` pass.
- [ ] Step 5: commit.

### Task 3: Shortfall reason and refusal messages

**Files:** Modify `manufacturing/models.py`, `manufacturing/services.py`,
`tests/manufacturing/test_production_postings.py`. Create
`manufacturing/migrations/0008_order_shortfall_reason.py` (field, CHECK, trigger).

- [ ] Step 1: tests: `test_close_short_needs_a_reason` (output 9 of 10, no reason →
  `OrderValidationError` matching "shortfall"; with reason → stored), `test_close_complete_refuses_a_reason`,
  `test_shortfall_follows_output_reversal`, `test_close_replay_compares_the_reason`,
  `test_database_requires_shortfall_reason_iff_short` (raw update to CLOSED without reason when
  short, with reason when complete, reason on OPEN → `IntegrityError`),
  `test_refusals_name_each_held_lot` (cancel and close messages contain `LED-CHIP lot L1 holds 40`
  and a second lot). Update M5.2b close calls on short orders to pass `shortfall_reason`.
- [ ] Step 2: run, expect failures.
- [ ] Step 3: implement; `close_production_order(..., shortfall_reason: str | None = None)`.
- [ ] Step 4: full suite, Ruff, `makemigrations --check`, migrate down to
  `manufacturing 0006` / `inventory 0012` and back.
- [ ] Step 5: commit.

### Task 4: Documentation and PR

- [ ] Assignment record (delivered, rulings, RED/GREEN, verification, review), TASKS.md Progress
  log, PR with template checklist. Scrutinize per `docs/SCRUTINIZE.md` before opening.
