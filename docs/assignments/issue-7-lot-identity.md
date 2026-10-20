# Issue #7 assignment and handoff record

## Assignment

- Repository: `porntaned/ERP-for-Factory`
- Issue: [#7 — Lot identity foundation](https://github.com/porntaned/ERP-for-Factory/issues/7)
- Branch: `feat/lot-identity`
- Base SHA: `d31ac7a9f5286353ed05a46ccc6ce3be3c1678e1`
- Manager and integrator: `/root`
- Scope reviewer: `/root/lot_scope_reviewer` — read-only issue-boundary review
- Test reviewer: `/root/lot_test_reviewer` — read-only TDD RED review
- Test writer: `/root/lot_tdd_writer` — PostgreSQL acceptance tests only
- Model implementer: unassigned — future `inventory.Lot` model and migration
- Independent implementation reviewer: unassigned — future read-only end-to-end Scrutinize

## Authorized scope

Create the smallest Lot identity needed before stock movements: an Item-scoped internal Lot code.
Prove the locked identity, database constraints, protected parent and concurrent duplicate behavior
on PostgreSQL before implementation.

## Exclusions

No stock quantities or movements, warehouse ownership, supplier lot, serial numbers, manufacture or
expiry dates, Hold/Released status, quality decisions, valuation, audit workflow, UI, API, merge or
deployment.

## Locked schema decisions

- `inventory.Lot` belongs to one `catalog.Item`; deleting an Item referenced by a Lot is protected.
- `code` is the internal Lot code and uses the existing repository `CODE_PATTERN`: 1–32 ASCII
  characters, starting with `A`–`Z`, followed by `A`–`Z`, `0`–`9`, `_` or `-`.
- Lot identity is unique on `(item, code)`. The same code may identify Lots of different Items.
- `item` and `code` are non-null. No additional Lot fields are authorized by this issue.

## Acceptance for this handoff

1. Tests collect while `inventory` and `inventory.Lot` are absent, then fail for that missing model.
2. PostgreSQL tests cover null fields, invalid Item references and code format boundaries.
3. Tests prove `(item, code)` uniqueness and allow the same code for different Items.
4. Tests cover protected Item deletion and concurrent duplicate writes.
5. A genuine TDD RED is published and independently reviewed before implementation.
6. A future implementation turns the complete suite GREEN without migration drift.
7. A future independent reviewer traces the exact implementation commit before an owner-review PR.

## Handoff evidence

Pending TDD RED commit, PostgreSQL CI run and independent test review.

