# Issue #9 PostgreSQL GREEN evidence

- Tested commit: [`23286336a752afd3791f4a41881f83f339bbe8a9`](https://github.com/porntaned/ERP-for-Factory/commit/23286336a752afd3791f4a41881f83f339bbe8a9)
- Branch: `codex/role-warehouse-permissions`
- GitHub Actions run: [Foundation #28](https://github.com/porntaned/ERP-for-Factory/actions/runs/39444111594)
- Job: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39444111594/job/118701348927)
- Environment: GitHub-hosted Ubuntu 24.04 runner with PostgreSQL 18.6
- Result: GREEN

## Verified path

1. Checked out the exact implementation commit.
2. Installed uv 0.13.1 and Python 3.14.8.
3. Synchronized Django 5.2.18, psycopg 3.3.6 and locked development dependencies.
4. Ran `python manage.py check`: no issues.
5. Connected to `vendor=postgresql`, server version 18.6.
6. Ran `python manage.py makemigrations --check --dry-run`: no drift.
7. Applied all migrations to fresh PostgreSQL, including `access_control.0001_initial`.
8. Ran Ruff: all checks passed.
9. Ran the complete pytest suite: `174 passed in 2.39s`.

## Proven behavior

- Django's default User identity is enabled without a custom User or third-party dependency.
- The assignment stores exactly User, Warehouse and one of four locked roles.
- PostgreSQL enforces required and protected references, valid roles and unique exact tuples.
- Concurrent exact duplicates produce one row and one `IntegrityError`.
- Policy checks require an active saved User, an exact Warehouse and an explicitly allowed role.
- Role evaluation and authorized-Warehouse queries do not leak across Users, Warehouses, Plants or
  Organizations, including duplicate Warehouse codes in different scopes.
- Empty, mixed, unsupported, structurally invalid and unhashable requested roles fail closed.
- Superuser status does not bypass the explicit assignment.
- Deleting an assignment revokes both boolean access and the authorized-Warehouse query.
- Synthetic test Users have unusable passwords; no demo credential or real data is stored.

## Local preparation

Synthetic local-check values were used for configuration-only commands. Django system checks,
migration drift checks, test collection, Ruff and `git diff --check` passed. Local PostgreSQL access
was unavailable, so every database behavior claim above is supported by the GitHub Actions run.
