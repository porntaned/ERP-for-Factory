# Issue #5 assignment and handoff record

## Assignment

- Repository: `porntaned/ERP-for-Factory`
- Issue: [#5 — Issue 2: Item and unit of measure foundation](https://github.com/porntaned/ERP-for-Factory/issues/5)
- Branch: `feat/item-uom-foundation`
- Base SHA: `050f6c645dfa065071ca055c46e4d9bdefbf574e`
- Manager and integrator: `/root`
- Test designer: `/root/tdd_red_design` — read-only acceptance and RED-path design
- Schema reviewer: `/root/m2_schema_reviewer` — read-only catalog-boundary review
- Model implementer: `/root/m2_models_implementer` — catalog models and initial migration
- Independent reviewer: `/root/independent_scrutinize` — read-only end-to-end Scrutinize

## Authorized scope

Create the smallest catalog foundation needed before lot identity and inventory: a global unit of
measure reference and organization-scoped Item master data. Prove the behavior on PostgreSQL before
opening an owner-review pull request.

## Exclusions

No Lot or serial identity, stock quantity or movement, unit conversion, supplier/customer data,
roles or warehouse permissions, audit, Hold/Released status, UI, API, merge or deployment.

## Locked schema decisions

- Both codes use the existing repository rule: 1–32 ASCII characters, starting with `A`–`Z`,
  followed by `A`–`Z`, `0`–`9`, `_` or `-`.
- Both human-readable names use `display_name`; they are non-null and may contain Unicode. Empty
  names are not prohibited by this issue.
- Item stores `base_uom` and the exact type values `RAW`, `WIP` or `FINISHED`.
- UOM is global. Item code is unique only within its Organization.

## Acceptance for this handoff

1. `catalog.UnitOfMeasure` has a non-null Unicode name and globally unique uppercase code.
2. `catalog.Item` belongs to `facilities.Organization`, uses a protected base unit, and has a
   database-constrained type of raw material, work in progress or finished good.
3. Item code is uppercase-format constrained and unique within its Organization.
4. Database tests cover required fields, invalid references, deletion protection, code and type
   constraints, Unicode names and concurrent duplicate writes on PostgreSQL.
5. A genuine TDD RED is published before implementation.
6. The implementation turns the complete suite GREEN without migration drift.
7. An independent reviewer traces the exact implementation commit and records a verdict.

## Handoff evidence

- RED commit: [`ca4dacbdc349ff7b4fcf5a3be10035c02e6f2c28`](https://github.com/porntaned/ERP-for-Factory/commit/ca4dacbdc349ff7b4fcf5a3be10035c02e6f2c28)
- RED run: [Foundation #8](https://github.com/porntaned/ERP-for-Factory/actions/runs/39389877487)
- RED record: [PostgreSQL TDD RED evidence](../evidence/issue-5-tdd-red.md)
- RED review: [Independent TDD RED review](../reviews/issue-5-tdd-red-independent-review.md)

GREEN implementation, final handoff, independent implementation review and pull request are
pending. No merge or deployment is authorized.
