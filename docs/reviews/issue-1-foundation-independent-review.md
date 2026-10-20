# Independent Scrutinize — Issue #1 implementation

- Reviewer: `/root/independent_scrutinize`
- Review type: independent, read-only end-to-end trace
- Initial implementation reviewed: [`7db1db96f810603650807abce5f0999c53bfa388`](https://github.com/porntaned/ERP-for-Factory/commit/7db1db96f810603650807abce5f0999c53bfa388)
- Repaired commit re-reviewed: [`8fdb446669c47f892774c2fba2c2093ba4d1c1e8`](https://github.com/porntaned/ERP-for-Factory/commit/8fdb446669c47f892774c2fba2c2093ba4d1c1e8)
- Execution evidence: [Foundation #4](https://github.com/porntaned/ERP-for-Factory/actions/runs/39369435238)
- Final verdict: `ship`

## Intent and smaller-alternative check

The change supplies only the Organization → Plant → Warehouse data foundation required by Issue
#1. The reviewer considered a single generic hierarchy model, but rejected it because it would
weaken the typed parent relationships and scoped uniqueness contracts. Keeping the three models
in one `facilities` app is the smallest design that preserves those contracts without adding an
API, UI, admin customization or unrelated ERP behavior.

## Trace and verification

The reviewer traced Django app registration through model loading, generated migration, fresh
PostgreSQL migration, ORM writes and database constraints. The trace covered valid hierarchy
creation, all uniqueness scopes, invalid parent IDs, code-format boundaries, separate deletion
graphs, Thai display names and concurrent duplicate Warehouse writes. The GitHub run checked out
the exact repaired SHA, connected to PostgreSQL 18.6, detected no migration drift, applied the
initial migration, passed Ruff and completed all 51 tests.

## Finding and repair

### Required-field constraints lacked direct regression tests

- **Finding:** the initial implementation relied on Django-generated `NOT NULL` columns but did
  not directly exercise them at the database boundary.
- **Why it matters:** a future nullable-field change could weaken the schema while the original
  behavior suite remained green.
- **Evidence:** the initial 43-test suite covered hierarchy, uniqueness, format, foreign keys,
  deletion, Unicode and concurrency, but no test wrote `NULL` to each required field.
- **Suggested change:** add parameterized direct database writes for every required business and
  parent field.
- **Repair:** commit `8fdb446` added eight cases for Organization `code`/`display_name`, Plant
  `organization_id`/`code`/`display_name`, and Warehouse `plant_id`/`code`/`display_name`.

The re-review confirmed that every case changes only its target field, writes through the ORM
without model validation, and asserts PostgreSQL `IntegrityError` inside a transaction. It found
no blocker, major or remaining minor issue and made no repository edits.
