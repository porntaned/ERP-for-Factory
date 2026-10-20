# Issue #7 Lot identity independent review

- Reviewer: `/root/lot_red_independent_review`
- Role: independent read-only reviewer
- Reviewed commit: [`c66cab65bb0f1dcb7dd1131514446651fecc47cf`](https://github.com/porntaned/ERP-for-Factory/commit/c66cab65bb0f1dcb7dd1131514446651fecc47cf)
- PostgreSQL evidence: [Foundation #18](https://github.com/porntaned/ERP-for-Factory/actions/runs/39395440223)
- Verdict: `ship`
- Findings: no blocker, major or minor

## Intent and simpler alternative

The implementation adds the smallest persistent Item-scoped Lot identity needed by later Inventory,
Manufacturing and Quality work. Storing an Item and Lot string directly on future movements would
avoid a model now, but it would duplicate identity and weaken traceability. A separate two-field Lot
is the smaller sound domain boundary.

## End-to-end trace

1. `config/settings.py` registers `inventory.apps.InventoryConfig`.
2. `inventory/apps.py` loads the new application.
3. `inventory/models.py` defines only `item` and `code`, protects Item deletion, applies the shared
   internal code regex and makes `(item, code)` unique.
4. `inventory/migrations/0001_initial.py` depends on `catalog.0001_initial` and creates the matching
   table, foreign key and constraints.
5. `catalog.Item` continues to own Organization and base UOM, so Lot derives ownership without a
   second Organization field or a cross-organization mismatch path.
6. PostgreSQL tests exercise direct writes, deletion, constraint errors and two concurrent database
   connections rather than `full_clean` or mocks.

## Verification

The tests lock the exact concrete fields, valid and invalid code boundaries, Item-scoped uniqueness,
same-code reuse for another Item, Item deletion protection, NULL and invalid-FK handling, and the
concurrent duplicate path. The commit contains only settings plus the inventory app and migration;
it adds no stock, warehouse, quantity, status, audit, UI, API, valuation, deployment or dependency.

CI run #18 tested the exact commit on PostgreSQL 18.6. Django checks, migration drift, fresh
migrations and Ruff passed, followed by 115 passing tests in 1.15 seconds. The model and migration
match and no claim depends on SQLite or a mock.

## Verdict

`ship` — the exact implementation satisfies the locked two-field contract and its PostgreSQL tests
without crossing the later Inventory, Quality or workflow boundaries.
