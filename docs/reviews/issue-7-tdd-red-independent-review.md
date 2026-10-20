# Issue #7 TDD RED independent review

- Reviewer: `/root/lot_red_independent_review`
- Role: independent read-only reviewer
- Reviewed commit: [`dab4b460bb5f0fea476a72d8c609746e02c708d1`](https://github.com/porntaned/ERP-for-Factory/commit/dab4b460bb5f0fea476a72d8c609746e02c708d1)
- PostgreSQL evidence: [Foundation #16](https://github.com/porntaned/ERP-for-Factory/actions/runs/39394726202)
- Final verdict: `ship`

## Intent and simpler alternative

The change specifies the smallest persistent Lot identity that later Inventory, Manufacturing and
Quality work can reference. The two-field `Lot(item, code)` contract is already the smaller useful
alternative: deferring identity into stock movements would duplicate identifiers, while adding
Organization, warehouse, quantity, status or dates would cross later domain boundaries.

## Trace and verification

The reviewer traced Issue #7 and its assignment through fixtures, each database behavior test, the
CI trigger and the absence of application implementation. The suite covers code boundaries, direct
NULL and invalid-FK writes, Item-scoped uniqueness, the same code on different Items, protected Item
deletion and a two-connection PostgreSQL duplicate race. The concurrency harness joins both workers,
surfaces unexpected thread failures and requires exactly one created row and one `IntegrityError`.

The first review found that an implementation could add a duplicated Organization or other
persistent fields while the behavior tests still passed. The repair added an exact concrete-field
assertion for `{id, item, code}`. Re-review found no remaining blocker, major or minor finding.

CI at the reviewed commit connected to PostgreSQL 18.6, completed configuration, migration and Ruff
checks, passed all 96 pre-existing tests, and failed all 19 Lot cases only because `inventory.Lot`
was absent. No application code or migration was included in the reviewed commit.

## Verdict

`ship` — the RED suite locks the authorized two-field schema and fails only for the missing Lot
implementation while the complete existing regression suite remains GREEN.
