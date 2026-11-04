# M5.1 — versioned BOM and production order (design spec)

Repository `porntaned/ERP-for-Factory`; branch `claude/dreamy-volta-9v3i8u`; base `main` `1158ada`.
[Issue #69](https://github.com/porntaned/ERP-for-Factory/issues/69). Status: **merged** (PR #70 at `5891ec7`, 2026-11-04;
"implemented, PR awaiting owner review" held until then — historical) (the spec was approved 2026-11-04; "awaiting owner review, no code yet" held until
then — historical). Designed with the `superpowers:brainstorming` skill (architectural path); the owner
answered the design questions and approved the design in chat on 2026-11-04.

## Goal

A new `manufacturing` app holds bills of materials with versions and an approval step, and
production orders that point at an approved version. M5.1 moves **no stock**: issue, return,
consumption and output are M5.2; lot genealogy is M5.3.

## Owner decisions (2026-11-04)

1. An ACTIVE BOM version is locked; a change needs a new version. One ACTIVE version per item.
2. PRODUCTION creates a BOM draft; APPROVER activates it and must not be the creator.
3. A production order names a production-line warehouse (`LINE-1`) and an output warehouse
   (`FG`). M5.2 will issue RM → LINE-1, return LINE-1 → RM, consume at LINE-1 and receive output
   at FG through Inventory commands.
4. Order status in M5.1: OPEN / CANCELLED. CLOSED arrives with M5.2.
5. Structure: a new `manufacturing` app owns both BOM and order (not `catalog`, not JSON lines).

## Data model (`manufacturing/models.py`)

**BillOfMaterials**

| Field | Rule |
|---|---|
| `item` | FK `catalog.Item`, `item_type` FINISHED or WIP |
| `version` | integer ≥ 1, unique per item; the command locks the item row and assigns max + 1, so two concurrent drafts get 1 and 2 |
| `status` | DRAFT / ACTIVE / RETIRED |
| `created_by` | user, required |
| `approved_by`, `approved_at` | null while DRAFT; required for ACTIVE and RETIRED; `approved_by <> created_by` |
| `request_id` | UUID, unique (draft command key) |
| `approval_request_id` | UUID, unique, null while DRAFT (approval command key; added while planning) |

Partial unique index: at most one ACTIVE row per item.

**BomLine**

| Field | Rule |
|---|---|
| `bom` | FK BillOfMaterials |
| `component` | FK `catalog.Item`, RAW or WIP, same organization as `bom.item`, not `bom.item` |
| `quantity_per` | quantity of the component's base UOM per one unit of `bom.item`; `> 0`; `ExactQuantityField(max_digits=20, decimal_places=6)` like the ledger |

Unique `(bom, component)`. A draft needs at least one line (checked by the command; the
database cannot see "at least one child" at insert time).

**ProductionOrder**

| Field | Rule |
|---|---|
| `bom` | FK BillOfMaterials, ACTIVE when the order is created |
| `quantity` | units of `bom.item` to produce, `> 0`, same quantity field |
| `line_warehouse`, `output_warehouse` | same plant, different warehouses, plant in the item's organization |
| `status` | OPEN / CANCELLED |
| `created_by`, `created_at` | required |
| `cancelled_by`, `cancelled_at`, `cancel_reason` | set together, only when CANCELLED |
| `request_id`, `cancel_request_id` | UUID, unique |

An order keeps pointing at its version after that version is RETIRED.

## Rules enforced by PostgreSQL (triggers in migrations, as in `inventory`)

- BomLine insert, update or delete is rejected unless its BOM is DRAFT.
- BOM status moves forward only: DRAFT → ACTIVE → RETIRED. Item, version, creator and request
  UUID never change; approval fields are written once.
- BOM item type, line component type and organization, and order warehouse plant/organization
  are checked by triggers (cross-table, so not plain CHECK constraints).
- Order: only OPEN → CANCELLED with its cancel fields; nothing else changes; no deletes.
- An order can be inserted only for an ACTIVE BOM.

## Commands (`manufacturing/services.py`)

Each command takes a `request_id` UUID: an exact repeat replays the stored result, a different
payload with the same UUID is a conflict, as in M4. Errors are split into Validation,
Authorization and Conflict classes.

| Command | Authority |
|---|---|
| `create_bom_draft(item, lines, actor, request_id)` → next version, DRAFT | PRODUCTION at any warehouse of a plant in the item's organization |
| `approve_bom(bom, actor, request_id)` → ACTIVE; the previous ACTIVE version → RETIRED in the same transaction, rows locked | APPROVER at any warehouse in the organization; not the creator |
| `create_production_order(bom, quantity, line_warehouse, output_warehouse, actor, request_id)` | PRODUCTION at both warehouses |
| `cancel_production_order(order, actor, reason, request_id)` | PRODUCTION at both warehouses |

Authority is checked inside the transaction after the locks, by queries that lock the actor and
the grants (as `inventory/reversals.py:_lock_authority`), not by `access_control.policies` — corrected
2026-11-04: the spec first named `has_warehouse_role` / `warehouses_for_user`, which do not lock and
were replaced by the risk-5 fix the owner approved. Request UUIDs join the shared registry:
`BOM_DRAFT`, `BOM_APPROVE`, `ORDER_CREATE` and `ORDER_CANCEL` are added to `REQUEST_KEY_COMMANDS`
(`inventory/models.py`, inventory migration 0010), and manufacturing triggers call
`manufacturing_register_request_key(command, column)` (manufacturing migration 0002), the same
insert-or-keep logic as inventory's function but with the key column as an argument so approval and
cancel keys register on UPDATE.

## Demo data (`seed_demo`)

Add warehouse `LINE-1`, user `demo-production` (PRODUCTION at LINE-1, FG, RM-A, RM-B), APPROVER
for `demo-approver` where approval needs it, and BOM LAMP-A19 v1 = LED-CHIP 4 + DRIVER 1 created
by `demo-production` and approved by `demo-approver`. Fixed request UUIDs keep it rerunnable; it
writes no new ledger entries.

## Tests (`tests/manufacturing/`, PostgreSQL)

- Database: line change after ACTIVE, two ACTIVE versions, approver = creator, wrong item type,
  component from another organization, cross-plant order, order on a DRAFT BOM, status moving
  backwards, deletes — each rejected, including through raw SQL.
- Commands: authority per role and warehouse, replay, payload conflict, cross-command key
  conflict, concurrent approval of two drafts of one item ends with one ACTIVE.
- `seed_demo` reruns without duplicates or ledger entries.
- CI: a `tests/manufacturing` step in `.github/workflows/foundation.yml`.

## Out of scope

Stock movements, screens, lot genealogy, costing, routing or work centres, scrap, planning,
Deploy.

## Delivered

- `manufacturing` app: models and CHECK/unique constraints (`0001_initial`), PostgreSQL triggers
  (`0002_database_rules`, reversible), commands in `manufacturing/services.py`.
- `inventory/quantities.py`: the ledger quantity rule shared by receipt, transfer and
  manufacturing; receipt and transfer messages unchanged.
- `inventory` migration 0010: four manufacturing request-key commands.
- `seed_demo`: LINE-1, `demo-production` (PRODUCTION at RM-A, RM-B, LINE-1, FG), LAMP-A19 v1 =
  4 LED-CHIP + 1 DRIVER drafted by `demo-production`, approved by `demo-approver`.
- CI step `Run manufacturing tests`.
- Plan: [`m51-plan.md`](m51-plan.md) (5 tasks), executed inline by one agent with
  `superpowers:executing-plans` and `test-driven-development`, as the owner chose.

## Rulings made while building

1. A BOM row can be inserted only as DRAFT (trigger). Commands always insert DRAFT.
2. Draft lines may be deleted while DRAFT (spec); the header is never deleted. A test that
   expected draft-line deletes to fail was corrected.
3. The quantity helper is split into `is_positive_bounded` and `fits_six_places` so receipt and
   transfer keep their two distinct messages.
4. Every command checks current authority before answering a replay (M4.3.6 rule); found while
   comparing with M4, `test_replay_requires_current_authority` RED → GREEN.
5. `create_production_order` checks the warehouses' plant and organization before authority, so a
   malformed request gets a data error.
6. `tests/web/test_scaffold.py` (M7.1) pinned the old seed: expectations now include LINE-1 and the
   `BOM_DRAFT` / `BOM_APPROVE` keys.

## RED / GREEN

| Task | RED observed | GREEN |
|---|---|---|
| 1 Models | 16 tests: `ModuleNotFoundError: manufacturing` | 16 passed |
| 2 DB rules | 19 failed; one test passed for the wrong reason (unique violation) and was fixed to fail first | 37 passed |
| 3 BOM commands | collection error (no `manufacturing.services`); later the replay-authority test | 64 passed |
| 4 Order commands | import error (`OrderAuthorizationError`); 2 bad-warehouse cases failed with an authority error | 88 passed |
| 5 Seed | `assert 0 == 1` (no LINE-1); then 3 M7.1 seed tests pinned old contents | 125 passed (manufacturing + web) |

## Self-review findings fixed

Review type: **self-review only** (the owner chose no subagents); `scrutinize` pass on the branch.

1. `approve_bom` would activate a draft with no lines (possible only through raw writes) —
   `test_approve_rejects_draft_without_lines` RED → GREEN.
2. `approve_bom` used `select_for_update()` with `select_related("item")`, which also locked the
   `catalog_item` row FOR UPDATE and blocked stock commands that take FOR SHARE on the item; now
   `of=("self",)` — `test_approval_does_not_lock_the_item_row` RED (`OperationalError` on
   `FOR SHARE NOWAIT`) → GREEN.

Deferred minors (not fixed, for the owner to decide):

- `create_bom_draft` locks the item row FOR NO KEY UPDATE to number versions; stock commands on the
  same item wait briefly behind it (no deadlock). Relevant when M5.2 receives output.
- Orders on the same BOM queue behind each other (`FOR UPDATE`); `FOR SHARE` would let them run
  together but needs raw SQL in Django.
- If a passed warehouse no longer exists, the plant check can report a misleading error;
  warehouses are PROTECTed, so this needs a raw delete.

## Verification (development check, not evidence of record)

Environment: PostgreSQL 16.15 (Ubuntu), Python 3.14.6 via `UV_PYTHON=3.14.6` (3.14.8 is not
available in this session). Tested commit `38b297febea9fd4a12df7a001d6e6751b597de99`.

| Command | Result |
|---|---|
| `uv run pytest -q` | 850 passed |
| `uv run pytest -q tests/manufacturing` | 91 passed |
| `uv run ruff check .` / `uv run ruff format --check .` | clean |
| `uv run python manage.py makemigrations --check --dry-run` | No changes detected |
| `migrate manufacturing zero` → `migrate inventory 0009` → `migrate` | reversible |

CI evidence of record: the CI comment on the PR.

## Next steps

After merge: post-merge docs PR (tick M5.1 in `docs/TASKS.md`, closeout here). M5.2 needs owner
decisions first: issuing above the BOM, scrap, when an order closes, and whether issued
materials must be RELEASED.

## Closeout (2026-11-04)

PR CI run [#198](https://github.com/porntaned/ERP-for-Factory/actions/runs/41859287249) on head `db8144b`
(tested as merge `ef4e11f`): PostgreSQL 18.6, Python 3.14.8, **850 passed**
([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/70#issuecomment-6634877953)). Merged on the
owner's instruction in chat: PR #70 at `5891ec7172c37cb564bb7169f3011b87a80e2972`;
[main CI #199](https://github.com/porntaned/ERP-for-Factory/actions/runs/41859794833): **850 passed**.
Issue #69 closed. Review remained self-review only.
