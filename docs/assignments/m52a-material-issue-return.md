# M5.2a — issue and return material for a production order

Repository `porntaned/ERP-for-Factory`; branch `claude/dreamy-volta-9v3i8u`; base `main` `eb24e25`.
[Issue #72](https://github.com/porntaned/ERP-for-Factory/issues/72). Status: **PR awaiting CI**.

## Owner decisions (chat, 2026-11-04)

1. Net issue (issued − returned) per component never exceeds order quantity × `quantity_per`.
2. Material must be RELEASED at the source to be issued.
3. The owner authorised continuous work through M5–M6 with self-merge after green CI, strictly
   inside the TASKS.md scope, and asked to stop only after a fully merged slice.

Later slices already decided: closing an order needs zero material on the line (return or scrap
with APPROVER); output enters FG as HOLD; inspection PASS → RELEASED, FAIL → REJECTED.

## Delivered

- `inventory/transfers.py`: `post_production_transfer` — the same posting, locks, replay and
  stock checks as `transfer_stock`, with PRODUCTION authority at both ends; the Quality gate is
  the source for an issue and the destination for a return. `transfer_stock` is unchanged
  (WAREHOUSE, source gate, same messages).
- `manufacturing.ProductionMaterialMovement` (ISSUE / RETURN) links one `StockTransfer` to its
  order; lot, quantity, warehouses and actor stay on Inventory's ledger entries.
- `issue_material(order, lot, source_warehouse, quantity, actor, reason, request_id)` and
  `return_material(order, lot, destination_warehouse, quantity, actor, reason, request_id)`.
- PostgreSQL (migration 0004, reversible): on insert the order row is locked; the order must be
  OPEN; an issue lands on the order line from elsewhere, a return leaves it; the Lot item must be a
  BOM component; net issue ≤ requirement; a return ≤ what the order holds of that Lot; movements
  are immutable; an order holding material cannot be cancelled.
- `cancel_production_order` refuses while the order holds material (new rule, see rulings).

## Rulings

1. Production movements go through a separate Inventory interface rather than a role argument on
   `transfer_stock`, so a PRODUCTION user still cannot make arbitrary transfers.
2. A return's Quality gate is the destination: material comes back only where its Lot is RELEASED
   (normally the warehouse it came from). The line's own disposition (HOLD by default) is not used.
3. The return limit is per order and Lot (issued − returned of that Lot by that order), so one
   order cannot return another order's material on a shared line.
4. Cancelling with material on the line would strand stock, so cancel now requires zero holdings.
5. The transfer's request UUID is the movement's key (registered as TRANSFER); a plain transfer's
   key is never adopted as an issue.
6. Manufacturing's early authority check is an unlocked read; Inventory's locked check is
   authoritative. This avoids locking the actor before the Lot, which would invert Inventory's
   lock order.

## RED / GREEN

RED: collection error, `ProductionMaterialMovement` missing. GREEN: 20 tests in
`tests/manufacturing/test_material_movements.py` (cap, multi-lot cap, BOM membership, Quality,
authority, open order, replay/conflict, plain-transfer key, returns, cancel, DB rules,
immutability, concurrent issues against the cap).

## Verification (development check, not evidence of record)

PostgreSQL 16.15, Python 3.14.6. Tested commit `a5bee392db4cc35144d22306d5d80ee87b19ecf9`.

| Command | Result |
|---|---|
| `uv run pytest -q` | 870 passed |
| `uv run ruff check .` / `ruff format --check .` | clean |
| `makemigrations --check --dry-run` | No changes detected |
| `migrate manufacturing 0002` → `migrate` | reversible |

CI evidence of record: the CI comment on the PR.

## Review

Self-review only (`scrutinize` trace of the issue/return paths and the lock order).
