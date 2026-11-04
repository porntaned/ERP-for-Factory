# M5.1 — versioned BOM and production order (design spec)

Repository `porntaned/ERP-for-Factory`; branch `claude/dreamy-volta-9v3i8u`; base `main` `1158ada`.
[Issue #69](https://github.com/porntaned/ERP-for-Factory/issues/69). Status: **spec awaiting owner review**;
no code yet. Designed with the `superpowers:brainstorming` skill (architectural path); the owner
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

Authority uses `access_control.policies.has_warehouse_role` / `warehouses_for_user`. Request UUIDs
join the shared registry: `BOM_DRAFT`, `BOM_APPROVE`, `ORDER_CREATE` and `ORDER_CANCEL` are added
to `REQUEST_KEY_COMMANDS` (`inventory/models.py`, migration updating the CHECK), and manufacturing
triggers call `inventory_register_request_key()` from inventory migration 0007.

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

## Next steps

1. Owner reviews this spec.
2. Implementation plan with `superpowers:writing-plans`; owner reviews it and picks the execution
   method.
3. Build with `test-driven-development`, check with `verification-before-completion`, review with
   `scrutinize`, then a PR for the owner to merge.
