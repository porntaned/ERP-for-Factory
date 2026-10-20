# Issue #9 Warehouse role grants independent review

- Reviewer: `/root/m32_implementation_scrutinize`
- Reviewed implementation commit: [`23286336a752afd3791f4a41881f83f339bbe8a9`](https://github.com/porntaned/ERP-for-Factory/commit/23286336a752afd3791f4a41881f83f339bbe8a9)
- CI evidence: [Foundation #28](https://github.com/porntaned/ERP-for-Factory/actions/runs/39444111594), [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39444111594/job/118701348927)
- Method: `docs/SCRUTINIZE.md`

## Intent and simpler alternative

The change creates the smallest explicit Warehouse-scoped role boundary for synthetic ERP users.
Django Groups and model permissions are global and cannot express a Warehouse instance. Reusing
Django User with one assignment model and two policy functions is the smaller adequate approach;
Organization/Plant inheritance and a third-party object-permission package are not justified.

## End-to-end trace

1. `config.settings` enables Django contenttypes, auth and the `access_control` app.
2. The initial migration depends on the swappable User and Facilities migration, then creates the
   assignment table with protected foreign keys, a role check and exact-tuple uniqueness.
3. `WarehouseRoleAssignment` exposes only User, Warehouse and one of four locked roles.
4. Policy input is materialized once, structurally validated, normalized and checked against the
   supported role set before any authorization query runs.
5. The boolean policy queries the exact User primary key, Warehouse primary key and allowed roles.
6. The Warehouse query uses the same User and role predicates and applies `distinct()` when a User
   has multiple matching roles.
7. Deleting a grant changes both paths immediately; User or Warehouse deletion remains protected.

## Verification

The review traced anonymous, inactive, unsaved and cross-user inputs; sibling Warehouse, Plant and
Organization boundaries; duplicate Warehouse codes; mixed, mapping and unhashable role inputs;
superuser behavior; revocation; deletion; database role and uniqueness constraints; and concurrent
duplicate writes.

The first implementation review found that an unhashable `str` subclass could raise `TypeError`
instead of failing closed. The repaired exact commit normalizes string values before hashing and
adds a regression through both policy interfaces. The unsupported value now denies without an
exception, while a valid string subclass retains its valid role meaning.

GitHub Actions checked out the exact reviewed SHA, connected to PostgreSQL 18.6, applied fresh
migrations without drift, passed Ruff and completed the full suite: `174 passed in 2.39s`.

No blocker, major or minor finding remains.

**Verdict: `ship`.**
