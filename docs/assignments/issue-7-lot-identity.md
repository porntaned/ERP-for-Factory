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
- Independent TDD reviewer: `/root/lot_red_independent_review` — read-only exact-commit Scrutinize
- Model implementer: `/root/lot_model_implementer` — `inventory.Lot` model and migration
- Independent implementation reviewer: `/root/lot_red_independent_review` — read-only end-to-end Scrutinize

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

- RED commit: [`dab4b460bb5f0fea476a72d8c609746e02c708d1`](https://github.com/porntaned/ERP-for-Factory/commit/dab4b460bb5f0fea476a72d8c609746e02c708d1)
- RED run: [Foundation #16](https://github.com/porntaned/ERP-for-Factory/actions/runs/39394726202)
- RED record: [PostgreSQL TDD RED evidence](../evidence/issue-7-tdd-red.md)
- RED review: [Independent TDD RED review](../reviews/issue-7-tdd-red-independent-review.md)
- GREEN implementation: [`c66cab65bb0f1dcb7dd1131514446651fecc47cf`](https://github.com/porntaned/ERP-for-Factory/commit/c66cab65bb0f1dcb7dd1131514446651fecc47cf)
- GREEN run: [Foundation #18](https://github.com/porntaned/ERP-for-Factory/actions/runs/39395440223)
- GREEN record: [PostgreSQL GREEN evidence](../evidence/issue-7-green.md)
- Independent implementation review: [Issue #7 Lot review](../reviews/issue-7-lot-independent-review.md)
- Owner-review pull request: [#8 — Add Lot identity foundation](https://github.com/porntaned/ERP-for-Factory/pull/8)

The owner decides whether to merge PR #8. No merge or deployment is authorized.

