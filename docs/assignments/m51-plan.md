# M5.1 versioned BOM and production order — implementation plan

> **Execution:** the owner chose inline execution (no subagents), the same method as M4.7, using
> `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `manufacturing` app with versioned, approved BOMs and production orders that point at
an ACTIVE version, enforced by PostgreSQL and reachable only through four commands.

**Architecture:** Models and CHECK/unique constraints in `manufacturing/models.py`; cross-table and
lifecycle rules in PostgreSQL triggers (RunSQL migrations, inventory style); commands in
`manufacturing/services.py` use `access_control.policies` and the shared `RequestKey` registry.
No stock movement, no screens.

**Tech Stack:** Django 5.2, PostgreSQL 18.6 (CI), pytest-django, Ruff.

**Spec:** [`m51-bom-production-order.md`](m51-bom-production-order.md) (Issue #69).

## Global Constraints

- Quantities use `inventory.fields.ExactQuantityField(max_digits=20, decimal_places=6)` with the
  ledger's checks: `> 0`, `< 100000000000000`, equal to `Round(q, 6)`.
- Every command takes keyword-only args and a `request_id: UUID`; an exact repeat replays, a
  different payload raises the command's Conflict error, a key owned by another command raises
  Conflict.
- New `REQUEST_KEY_COMMANDS` values (≤ 12 chars): `BOM_DRAFT`, `BOM_APPROVE`, `ORDER_CREATE`,
  `ORDER_CANCEL`.
- Trigger errors use `ERRCODE = '23514'` (rule) or `'23505'` (key), like inventory.
- No stock ledger writes anywhere in M5.1.

## Spec additions decided while planning

- BOM gets `approval_request_id` (UUID, unique, null while DRAFT), the key of `approve_bom`, the
  same pattern as the order's `cancel_request_id`. The spec is updated in Task 1.
- `approve_bom` retires the previous ACTIVE row **before** activating the new one, because the
  partial unique index is checked per statement.

## Review Focus — risks and their fixes

Each risk gets a guard in the command (layer 1), a guard in PostgreSQL that holds even for raw
SQL (layer 2), and the tests that prove both. The owner asked for fixes, not only tests
(2026-11-04).

1. **Approving an ACTIVE or RETIRED version again with a new key.**
   Command: `approve_bom` locks every version of the item (`select_for_update().order_by("id")`)
   and reads the status after the lock; not DRAFT → `BomValidationError("only a DRAFT can be
   approved")` before any write. DB: status moves only DRAFT→ACTIVE→RETIRED; `approved_by`,
   `approved_at`, `approval_request_id` go NULL→value once, only on DRAFT→ACTIVE.
   Tests: `test_approve_rejects_non_draft` (row unchanged), raw SQL in
   `test_bom_status_moves_forward_only`.
2. **Replaying an approval after a newer version retired it.**
   Command: fixed order of checks — (a) a BOM with `approval_request_id = key`: same BOM and
   actor → return it whatever its status, otherwise `BomConflictError`; (b)
   `owned_by_other_command` → Conflict; (c) only then the DRAFT check of risk 1. DB: unique
   `approval_request_id` plus the shared `RequestKey`.
   Tests: `test_approve_replay_after_retirement`, `test_approve_key_reused_for_other_bom_conflicts`.
3. **An order on a version that is retired, or being retired concurrently.**
   Command: `create_production_order` locks the BOM row `FOR UPDATE` and checks ACTIVE after the
   lock; `approve_bom` locks all versions `FOR UPDATE`, so the two queue. Both lock in the same
   order (BOM rows by id → actor → grants) to avoid deadlock. DB: the order INSERT trigger reads
   the BOM status `FOR SHARE` and rejects anything but ACTIVE.
   Tests: `test_order_rejects_retired_bom`, `test_order_rejects_draft_bom`,
   `test_order_and_approval_serialize` (both directions, lock wait witnessed with `wait_for_lock`).
4. **Bad draft lines** (empty, duplicate, the item itself, float, zero or negative, seven
   decimals). Command: validated before the transaction opens; lines is a non-empty list of
   (saved Item, Decimal); unique component pks; component ≠ item. The quantity rule duplicated in
   `inventory/services.py:_validate_receipt_payload` and `inventory/transfers.py:_validate_payload`
   moves to `inventory/quantities.py:is_valid_quantity(q) -> bool` (no M4 behaviour change; M4
   tests must stay green) and is reused here. DB: quantity CHECKs, unique (bom, component), trigger
   for component type, organization and ≠ item.
   Tests: `test_draft_rejects_bad_lines` (7 cases, no rows and no `RequestKey` written).
5. **Authority from another organization, or an actor deactivated mid-command.**
   Command: authority is checked inside the transaction after the locks, as in
   `inventory/reversals.py:_lock_authority`: lock the actor and the relevant grants, require
   `is_active`; grants filter `warehouse__plant__organization = item.organization` and the role;
   an order needs PRODUCTION at both warehouses (id-set comparison); the approver must not be the
   creator. DB: CHECK `approved_by <> created_by` (role authority stays in commands, as in M4).
   Tests: `test_draft_authority_is_scoped_to_organization`, `test_order_requires_both_warehouses`,
   `test_inactive_actor_rejected` (every command), `test_approve_rejects_creator`.

---

### Task 1: Models, constraints and app registration

**Files:**
- Create: `manufacturing/__init__.py`, `manufacturing/apps.py`, `manufacturing/models.py`,
  `manufacturing/migrations/0001_initial.py` (generated)
- Modify: `config/settings.py` (add `"manufacturing.apps.ManufacturingConfig"` after quality),
  `docs/assignments/m51-bom-production-order.md` (add `approval_request_id`)
- Test: `tests/manufacturing/__init__.py`, `tests/manufacturing/conftest.py`,
  `tests/manufacturing/test_constraints.py`

**Interfaces — Produces:**
- `BomStatus` TextChoices `DRAFT`, `ACTIVE`, `RETIRED`; `OrderStatus` `OPEN`, `CANCELLED`
- `BillOfMaterials(item, version, status, created_by, created_at, approved_by, approved_at, request_id, approval_request_id)`, related_name `lines` on BomLine
- `BomLine(bom, component, quantity_per)`
- `ProductionOrder(bom, quantity, line_warehouse, output_warehouse, status, created_by, created_at, request_id, cancelled_by, cancelled_at, cancel_reason, cancel_request_id)`
- fixtures in `conftest.py`: `org`, `plant`, `wh` (dict RM-A, LINE-1, FG), `items` (dict LED-CHIP RAW, DRIVER RAW, LAMP FINISHED), `users` (dict production, approver, other), granted roles as in seed_demo

- [ ] **Step 1: Write failing constraint tests** — each inserts via the ORM and expects `IntegrityError`:
  `test_version_must_be_positive`, `test_version_unique_per_item`, `test_one_active_per_item`,
  `test_approver_differs_from_creator`, `test_draft_has_no_approval`,
  `test_active_requires_approval`, `test_line_quantity_positive_and_six_decimals`,
  `test_line_component_unique_per_bom`, `test_order_quantity_positive`,
  `test_order_warehouses_differ`, `test_cancel_fields_set_together_only_when_cancelled`.
- [ ] **Step 2: Run** `uv run pytest -q tests/manufacturing` → FAIL (app not installed).
- [ ] **Step 3: Implement models** with `CheckConstraint`/`UniqueConstraint` (partial
  `condition=Q(status="ACTIVE")` for one ACTIVE per item); `on_delete=PROTECT` everywhere;
  `created_at`/`approved_at` via `db_default=Now()` where set at insert. Register the app, run
  `makemigrations manufacturing`.
- [ ] **Step 4: Run** `uv run pytest -q tests/manufacturing` → PASS; `makemigrations --check` clean.
- [ ] **Step 5: Commit** `feat(manufacturing): BOM, BOM line and production order models`.

### Task 2: PostgreSQL rules and request-key registration

**Files:**
- Create: `manufacturing/migrations/0002_database_rules.py`,
  `inventory/migrations/0010_manufacturing_request_keys.py`
- Modify: `inventory/models.py` (`REQUEST_KEY_COMMANDS` + 4 values)
- Test: `tests/manufacturing/test_database_rules.py`

**Interfaces — Consumes:** Task 1 tables. **Produces:** SQL function
`manufacturing_register_request_key()` with `TG_ARGV[0]` = command, `TG_ARGV[1]` = column name,
reading the key as `(to_jsonb(NEW) ->> TG_ARGV[1])::uuid`, same insert-or-keep logic as
`inventory_register_request_key()`; it registers on INSERT (`request_id`) and on UPDATE when
`approval_request_id` / `cancel_request_id` goes from NULL to a value.

- [ ] **Step 1: Write failing tests** (raw SQL through `connection.cursor()` where the ORM would
  stop first), each expecting `IntegrityError`/`InternalError` with the trigger message:
  `test_bom_item_must_be_finished_or_wip`, `test_line_component_must_be_raw_or_wip`,
  `test_line_component_same_organization`, `test_line_component_not_bom_item`,
  `test_lines_locked_after_draft` (insert, update, delete), `test_bom_status_moves_forward_only`,
  `test_bom_identity_fields_immutable`, `test_bom_never_deleted`,
  `test_order_requires_active_bom`, `test_order_warehouses_same_plant_in_item_org`,
  `test_order_only_open_to_cancelled`, `test_order_never_deleted`,
  `test_keys_registered_per_command` (each of the 4 commands writes a `RequestKey` row),
  `test_key_shared_with_inventory_command_rejected`.
- [ ] **Step 2: Run** `uv run pytest -q tests/manufacturing/test_database_rules.py` → FAIL.
- [ ] **Step 3: Implement** inventory 0010 (`AlterField` choices + replace
  `request_key_command_valid` CHECK) and manufacturing 0002 (`RunSQL` with `reverse_sql`, BEFORE
  triggers, `ALTER COLUMN id SET GENERATED ALWAYS` as inventory does). Order rule check happens on
  INSERT only, so a later retirement does not block cancelling.
- [ ] **Step 4: Run** the file → PASS; full `tests/inventory` still PASS.
- [ ] **Step 5: Commit** `feat(manufacturing): enforce BOM and order rules in PostgreSQL`.

### Task 3: BOM commands

**Files:** Create `manufacturing/services.py` (BOM part), `inventory/quantities.py`; Modify `inventory/services.py`, `inventory/transfers.py` (use `is_valid_quantity`); Test `tests/manufacturing/test_bom_commands.py`

**Interfaces — Produces:**
- `class BomValidationError(ValueError)`, `BomAuthorizationError(Exception)`, `BomConflictError(Exception)`
- `create_bom_draft(*, item: Item, lines: Sequence[tuple[Item, Decimal]], actor, request_id: UUID) -> BillOfMaterials`
  — locks the item row, `version = max + 1`, authority: PRODUCTION at any warehouse whose plant is
  in `item.organization`
- `approve_bom(*, bom: BillOfMaterials, actor, request_id: UUID) -> BillOfMaterials`
  — locks all BOM rows of the item `ORDER BY id`; authority: APPROVER in the organization and
  `actor != created_by`

- [ ] **Step 1: Write failing tests:** `test_draft_creates_next_version_with_lines`,
  `test_draft_rejects_bad_lines` (parametrized: empty, duplicate component, item itself, float,
  seven decimals, zero), `test_draft_requires_production`,
  `test_draft_authority_is_scoped_to_organization`, `test_draft_replay_and_conflict`,
  `test_approve_activates_and_retires_previous`, `test_approve_rejects_creator`,
  `test_approve_rejects_non_draft`, `test_approve_replay_after_retirement`,
  `test_cross_command_key_conflict`, and with `@pytest.mark.django_db(transaction=True)`:
  `test_concurrent_drafts_get_versions_1_and_2`, `test_concurrent_approvals_leave_one_active`
  (reuse `wait_for_lock` from `tests/inventory/test_stock_ledger_concurrency.py`).
- [ ] **Step 2: Run** → FAIL (import error).
- [ ] **Step 3: Implement** following `inventory/reversals.py`: `_validate` → `transaction.atomic`
  → lock → `_prior_outcome` replay/conflict (`owned_by_other_command`) → write → on
  `IntegrityError` re-check prior outcome.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(manufacturing): BOM draft and approval commands`.

### Task 4: Production order commands

**Files:** Modify `manufacturing/services.py`; Test `tests/manufacturing/test_order_commands.py`

**Interfaces — Consumes:** Task 3 helpers. **Produces:**
- `OrderValidationError(ValueError)`, `OrderAuthorizationError(Exception)`, `OrderConflictError(Exception)`
- `create_production_order(*, bom, quantity: Decimal, line_warehouse, output_warehouse, actor, request_id: UUID) -> ProductionOrder` — locks the BOM row (`FOR SHARE`), requires ACTIVE
- `cancel_production_order(*, order, actor, reason: str, request_id: UUID) -> ProductionOrder` — OPEN only, nonblank reason
- authority for both: PRODUCTION at both warehouses

- [ ] **Step 1: Write failing tests:** `test_order_created_open_on_active_bom`,
  `test_order_rejects_draft_bom`, `test_order_rejects_retired_bom`,
  `test_order_rejects_bad_quantity` (parametrized), `test_order_rejects_cross_plant`,
  `test_order_requires_both_warehouses`, `test_order_replay_and_conflict`,
  `test_order_keeps_version_after_retirement`, `test_cancel_open_order`,
  `test_cancel_rejects_cancelled_and_blank_reason`, `test_cancel_replay_and_conflict`, and
  `@pytest.mark.django_db(transaction=True)` `test_order_and_approval_serialize`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** in the same structure as Task 3.
- [ ] **Step 4: Run** `uv run pytest -q tests/manufacturing` → PASS.
- [ ] **Step 5: Commit** `feat(manufacturing): production order create and cancel commands`.

### Task 5: Demo data, CI step and documentation

**Files:** Modify `demo/management/commands/seed_demo.py`, `.github/workflows/foundation.yml`
(step `Run manufacturing tests: uv run pytest -q tests/manufacturing --tb=short` before the full
suite), `docs/TASKS.md` (Progress log, สถานะปัจจุบัน), `docs/assignments/m51-bom-production-order.md`
(Verification, RED/GREEN, Review). Test `tests/manufacturing/test_seed_demo.py`.

- [ ] **Step 1: Write failing test** `test_seed_demo_adds_line_production_user_and_active_bom`:
  after two `seed_demo` runs there is one LINE-1, one `demo-production`, one LAMP-A19 BOM v1 ACTIVE
  with lines {LED-CHIP: 4, DRIVER: 1}, approved by `demo-approver`, created by `demo-production`,
  and `StockLedgerEntry` count equals the M4 seed (1).
- [ ] **Step 2: Run** → FAIL. **Step 3:** seed through `create_bom_draft` and `approve_bom` with
  `demo_key(...)` UUIDs; update the summary line. **Step 4:** run → PASS; existing
  `tests/web` still PASS (LINE-1 holds no stock, so balances are unchanged).
- [ ] **Step 5: Full verification** (development check): `uv run pytest -q`, `ruff check .`,
  `ruff format --check .`, `makemigrations --check --dry-run`; record SHA and results in the
  assignment record; self-review with `scrutinize`.
- [ ] **Step 6: Commit** `feat(demo): seed LINE-1, demo-production and LAMP-A19 BOM` + docs commit;
  push; open PR for the owner.
