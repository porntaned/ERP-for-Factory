# M6.1 PR 1 Implementation Plan

> **For agentic workers:** executed inline by one agent with `superpowers:executing-plans` and
> `superpowers:test-driven-development` (owner: solo, no sub-agents, self-review). Steps use
> checkbox (`- [ ]`) syntax.

**Goal:** an inspection record that is the only way to move a Lot-Warehouse out of HOLD (PASS →
RELEASED, FAIL → REJECTED), plus an APPROVER return from REJECTED to HOLD.

**Architecture:**
- Quality owns `LotInspection` and the new commands in `quality/services.py`.
- Each disposition event that leaves HOLD links its inspection one-to-one.
- PostgreSQL triggers re-check every rule on insert, so history written before M6.1 stays valid.
- Inventory and Manufacturing code do not change: they already require RELEASED.

**Tech Stack:** Django 5.2, PostgreSQL triggers in `RunSQL` migrations, pytest-django.

**Spec:** [`m61-inspection.md`](m61-inspection.md) ([Issue #96](https://github.com/porntaned/ERP-for-Factory/issues/96))

## Global Constraints

- Dispositions are `HOLD`, `RELEASED`, `REJECTED` (all fit the existing `varchar(8)`).
- Inspection `kind`:
  - `FINAL` if the Lot has an `OUTPUT` `ProductionPosting`
  - else `INCOMING` if it has a `StockReceipt`
  - else refused
- `result` is `PASS` → `RELEASED`, or `FAIL` → `REJECTED`.
- `sample_quantity` must pass `inventory.quantities.is_valid_quantity` and must not exceed
  `inventory.services.get_stock_balance` at that warehouse. The balance check is in the command only.
- `note` is nonblank, for PASS too.
- The command key is the event's `request_id`, registered as `DISPOSITION`. There is no new registry
  command.
- Lock order stays: Lot → actor → grant (as `transition_lot_disposition`).
- `transition_lot_disposition` allows only `RELEASED → HOLD`.
- `REJECTED → HOLD` needs APPROVER at the warehouse, and the actor must not be the rejecting
  inspector.
- Every migration is reversible. Tests run on PostgreSQL: `uv run --env-file .env pytest`.

## Review Focus

1. **A Lot transferred to a new warehouse arrives HOLD there.** Inspecting it must use the Lot's
   origin kind and that warehouse's balance → Task 2 test
   `test_transferred_lot_is_inspected_at_destination_with_origin_kind`.
2. **Two inspections race on one HOLD Lot-Warehouse.** One must win; the other gets a conflict and
   writes nothing → Task 2 test `test_concurrent_inspections_one_wins` (uses `blocked_action` from
   `tests/inventory/test_stock_receipt_concurrency.py`).
3. **The inspector is also an APPROVER.** The return to HOLD must still be refused, in the command and
   in the database → Task 3 tests.
4. **Rejected, returned to HOLD, then passed.** The Lot must become RELEASED and usable, with all
   three events kept → Task 3 test `test_reject_return_then_pass_releases`.
5. **An inspection with a valid event in the same transaction** must not trip the deferred check.
   An orphan inspection must fail at commit → Task 1 tests (`transaction=True`).

---

### Task 1: Model, migration and inspection command

**Files:**
- Modify: `quality/models.py`: `LotDisposition.REJECTED`; new `InspectionKind`, `InspectionResult`,
  `LotInspection`; `LotDispositionEvent.inspection = OneToOneField(LotInspection, null=True,
  on_delete=PROTECT, related_name="event")`
- Create: `quality/migrations/0006_lot_inspection.py`, containing:
  - the schema, with check constraints: `sample_quantity > 0`, `note` matches `\S`, `kind` and
    `result` in their values
  - `RunSQL` for the inspection insert trigger: organization, kind matches origin, nonblank note,
    `created_at := statement_timestamp()`
  - inspection append-only
  - a deferred constraint trigger: each inspection is referenced by exactly one event on the same
    Lot and warehouse
  - reverse SQL
- Modify: `quality/services.py`, adding:
  - `InspectionValidationError`, `InspectionConflictError`, and reuse of `DispositionAuthorizationError`
  - `inspection_kind(lot) -> str | None`
  - `record_inspection`
- Test: `tests/quality/test_inspection.py` (new)

**Interfaces:**
- Produces:
  - `record_inspection(*, lot, warehouse, result: str, sample_quantity: Decimal, note: str, actor,
    request_id: UUID) -> LotInspection`
  - `inspection_kind(lot) -> str | None`
  - `LotInspection` fields: `lot`, `warehouse`, `kind`, `result`, `sample_quantity`
    (`ExactQuantityField`, as the ledger), `note`, `inspector`, `created_at`
- Consumes: `get_stock_balance`, `is_valid_quantity`, `owned_by_other_command`, `_validate_pair`,
  `_resolve_existing_request` pattern.

- [ ] **Step 1: Write the failing tests**
  - Fixture `stocked`: org/plant/RM-A/FG, QUALITY user at RM-A and FG, APPROVER user. A receipt
    Lot `L1` with 10 received at RM-A via `receive_stock`. An output Lot made with the
    `tests/manufacturing/test_production_postings.py` `line` + `output` helpers (reuse them).
  - Tests:
    - `test_pass_releases_and_fail_rejects`:
      - PASS on L1 → `get_lot_disposition == "RELEASED"`, `event.inspection == inspection`,
        `inspection.kind == "INCOMING"`
      - FAIL on the second Lot → `"REJECTED"`
    - `test_kind_is_final_for_output_lot_and_mixed_lot`: the output Lot gives `"FINAL"`; after a
      receipt into the same Lot it is still `"FINAL"`
    - `test_lot_without_origin_is_refused`: `InspectionValidationError`, and no rows in either table
    - `test_refusals_write_nothing`, parametrized:
      - result `"MAYBE"`
      - quantity `D("0")`, `D("-1")`, `D("1.0000001")`, `D("11")` (above the balance of 10)
      - note `""`, `"  "`
      - request_id `"x"`
      - not HOLD (second inspection after a PASS)
    - `test_quality_at_this_warehouse_is_required`: APPROVER only, QUALITY at another warehouse,
      inactive user → `DispositionAuthorizationError`
    - `test_replay_and_conflicts`:
      - the same key and payload returns the same inspection, with one row
      - the same key with another note → `InspectionConflictError`
      - a key used by `receive_stock` → `InspectionConflictError`
    - `@pytest.mark.django_db(transaction=True) test_orphan_inspection_fails_at_commit`:
      `LotInspection.objects.create(...)` inside `transaction.atomic()` with no event →
      `IntegrityError` at commit
    - `test_database_refuses_wrong_kind_blank_note_and_mutation`: direct create with `kind="FINAL"`
      on L1 → IntegrityError; `.update(note="x")` and `.delete()` on a real inspection →
      IntegrityError
    - `test_migration_unapplies_and_reapplies` (`MigrationExecutor` pattern from
      `tests/manufacturing/test_production_reversal.py::test_migrations_unapply_only_without_reversals`)

- [ ] **Step 2: Run** `uv run --env-file .env pytest tests/quality/test_inspection.py -q`. Expected:
  collection or import errors (`record_inspection` missing). Record the RED output.

- [ ] **Step 3: Implement the model, the migration (`makemigrations quality` plus hand-written
  `RunSQL`) and `record_inspection`.**
  - The command locks the Lot first, then checks actor and grant.
  - Replay looks the key up with `LotDispositionEvent.objects.filter(request_id=…)` and compares
    the linked inspection's fields.
  - Then it creates the inspection and the event (`from="HOLD"`, `to` by result,
    `reason=note`, `inspection=`) inside one `transaction.atomic()`.
  - Retry on `IntegrityError` exactly as `transition_lot_disposition` does.
  - Import `get_stock_balance` inside the function if a module-level import makes a cycle
    (`inventory.transfer_policy` imports `quality.services`).

- [ ] **Step 4: Run** the new tests: GREEN. Run `tests/quality`: existing tests still pass, because
  no old path is blocked yet.

- [ ] **Step 5: Commit** `feat(quality): LotInspection and record_inspection (M6.1, Issue #96)`.

### Task 2: Move every HOLD→RELEASED caller to `record_inspection`

**Files:**
- Create: `tests/quality/helpers.py` with
  `release(lot, warehouse, actor, *, quantity=None, note="Synthetic inspection — PASS") -> LotInspection`.
  The quantity defaults to the current balance, and to 1 when the balance is 0 — this is refused,
  so the caller must receive first.
- Modify the 9 test modules that call `transition_lot_disposition` toward RELEASED:
  - `tests/inventory/test_atomic_transfer.py`
  - `tests/inventory/test_request_key_registry.py`
  - `tests/inventory/test_stock_receipt.py`
  - `tests/inventory/test_stock_receipt_concurrency.py`
  - `tests/inventory/test_transfer_quality.py`
  - `tests/inventory/test_transfer_workflow.py`
  - `tests/manufacturing/test_material_movements.py`
  - `tests/manufacturing/test_production_reversal.py`
  - `tests/web/test_inventory_screens.py`
  - plus `tests/quality/test_lot_disposition.py` and its `conftest.py` where they release.
  - A test that released a Lot-Warehouse with no stock receives stock first, or now asserts the
    refusal if that is what it tested.
- Modify `demo/management/commands/seed_demo.py:102` and `seed_production_demo.py:70` to use
  `record_inspection(result="PASS", sample_quantity=D("1"), note="Synthetic demo incoming inspection")`
  with the same `demo_key(...)` keys.
- Test: the existing suites, plus `tests/quality/test_inspection.py::test_transferred_lot_is_inspected_at_destination_with_origin_kind`
  and `test_concurrent_inspections_one_wins` (Review Focus 1–2).

- [ ] **Step 1:** Add the two Review Focus tests and run them. RED is expected only if the behaviour
  is missing. If they pass at once, note it: they guard behaviour and do not drive it (as in M5.5
  PR 1).
- [ ] **Step 2:** Convert the callers and seeds.
- [ ] **Step 3:** Run the full suite: everything passes. Release no longer bypasses inspection in
  tests or demo data.
- [ ] **Step 4:** Commit `test: release Lots through record_inspection (M6.1)`.

### Task 3: Close the old path; APPROVER return to HOLD

**Files:**
- Modify `quality/services.py`:
  - narrow `transition_lot_disposition` so any pair other than `RELEASED→HOLD` raises
    `DispositionValidationError("use record_inspection to leave HOLD; use return_rejected_to_hold for REJECTED")`
  - add `return_rejected_to_hold`
- Create: `quality/migrations/0007_inspection_transition_rules.py`, a `BEFORE INSERT` trigger on
  `quality_lotdispositionevent`:
  - `HOLD→RELEASED/REJECTED` needs an inspection on the same Lot and warehouse with the matching
    result
  - an event with an inspection must be one of those two
  - otherwise only `RELEASED→HOLD` or `REJECTED→HOLD`
  - `REJECTED→HOLD` needs an APPROVER grant for `NEW.actor_id` at `NEW.warehouse_id`, and the
    actor must differ from the inspector of the latest inspection with result FAIL for that pair
  - name the trigger so it sorts before `quality_lot_disposition_zz_request_key`
- Test: `tests/quality/test_inspection.py` (more tests); update `tests/quality/test_lot_disposition.py`
  where it expects the old pairs.

**Interfaces:**
- Produces: `return_rejected_to_hold(*, lot, warehouse, actor, reason: str, request_id: UUID) -> LotDispositionEvent`

- [ ] **Step 1: Write failing tests:**
  - `test_transition_cannot_leave_hold`
  - `test_transition_still_holds_a_released_lot`
  - `test_approver_returns_rejected_to_hold`
  - `test_inspector_cannot_return_even_as_approver` (command and direct insert)
  - `test_quality_only_cannot_return`
  - `test_reject_return_then_pass_releases`
  - `test_database_refuses_leaving_hold_without_matching_inspection`: direct
    `LotDispositionEvent.objects.create` HOLD→RELEASED without an inspection, and with a FAIL
    inspection → IntegrityError
  - `test_return_replay_and_conflict`
  - the migration round-trip for 0007
- [ ] **Step 2:** Run; RED (old pairs accepted, function missing). Record it.
- [ ] **Step 3:** Implement the narrowing, the new command, and migration 0007.
- [ ] **Step 4:** Run the tests: GREEN; then the full suite.
- [ ] **Step 5:** Commit `feat(quality): inspection-only release and APPROVER return to HOLD (M6.1)`.

### Task 4: Prove REJECTED is blocked by Inventory and Manufacturing

**Files:**
- Test: `tests/quality/test_inspection.py`:
  - `test_rejected_lot_cannot_be_transferred` (`TransferQualityError`)
  - `test_rejected_lot_cannot_be_issued_to_production` (the material-movement helpers;
    `MaterialQualityError` or the error `issue_material` raises today)
  - `test_rejected_destination_blocks_transfer_reversal` (`ReversalQualityError`)
- No product code. If any of these tests passes for the wrong reason or fails, stop and report it to
  the owner before changing Inventory.

- [ ] **Step 1:** Write the tests and run them. Expected: pass at once (guards). State this in the
  record.
- [ ] **Step 2:** Commit `test: REJECTED is blocked at the gate warehouse (M6.1)`.

### Task 5: Docs, demo walk and verification

**Files:**
- Modify:
  - `docs/assignments/m61-inspection.md`: delivered, RED/GREEN, verification, review
  - `docs/TASKS.md`: Progress log; M6.1 stays unticked until PR 2 is merged
  - `docs/DEVELOPMENT.md`: seed steps; "rerun on old DB needs `--reset`"
  - `README.md` only if the delivered summary changes

- [ ] **Step 1:** Run, as a development check:
  - `uv run --env-file .env pytest -q`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run --env-file .env python manage.py makemigrations --check --dry-run`
- [ ] **Step 2:** Do the demo walk on a disposable database:
  - `migrate`
  - `seed_production_demo --reset` (run it twice; the counts must not change)
  - check that RM-A Lots are RELEASED with INCOMING inspections and output Lots are HOLD
- [ ] **Step 3:** Run scrutinize per `docs/SCRUTINIZE.md` (self-review). Record the findings.
- [ ] **Step 4:** Commit, push, and open PR 1 with the template. Cite the CI comment once it is
  posted. Do not merge.
