# Issue #5 TDD RED independent review

- Reviewer: `/root/independent_scrutinize`
- Review type: independent, read-only Scrutinize
- Initial reviewed commit: `ca4dacbdc349ff7b4fcf5a3be10035c02e6f2c28`
- PostgreSQL run: [Foundation #8](https://github.com/porntaned/ERP-for-Factory/actions/runs/39389877487)
- Initial verdict: `fix-then-ship`

## Intent and simpler alternative

The change defines PostgreSQL acceptance tests before implementing global UOM and
organization-scoped Item identity. One sentinel RED test would be smaller, but would not lock the
code, type, FK, deletion and concurrency contracts. The parameterized suite is justified and uses
the existing test infrastructure without a new dependency.

## Finding and repair

**Major — the suite did not lock the documented empty-name contract.** The assignment explicitly
allows an empty `display_name`, while the initial tests covered Unicode non-empty values and NULL
rejection only. An implementation could therefore add a non-empty database constraint, pass the
suite and violate the locked decision.

The repair adds database-backed creation and refresh cases for both UnitOfMeasure and Item with
`display_name=""`. Repaired commit, CI run and re-review verdict are recorded after they exist.

## Verified coverage at the initial commit

The reviewer traced global UOM uniqueness, organization-scoped Item uniqueness, code boundaries,
the three allowed item types, invalid types, required fields, invalid FKs, separate deletion graphs
and concurrent duplicate Item creation. Run #8 checked out the exact commit, connected to
PostgreSQL 18.6, passed Django/migration/Ruff setup and all 51 existing tests, then failed all 43
catalog cases at the intended missing-model boundary.
