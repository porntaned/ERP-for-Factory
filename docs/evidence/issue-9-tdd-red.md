# Issue #9 PostgreSQL TDD RED evidence

- Tested commit: [`a58c6eb02efdb324c068343476bfc317f4c5657e`](https://github.com/porntaned/ERP-for-Factory/commit/a58c6eb02efdb324c068343476bfc317f4c5657e)
- Branch: `codex/role-warehouse-permissions`
- GitHub Actions run: [Foundation #26](https://github.com/porntaned/ERP-for-Factory/actions/runs/39435149544)
- Job: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39435149544/job/118670107134)
- Environment: GitHub-hosted Ubuntu 24.04 runner with PostgreSQL 18.6
- Result: expected RED

## Verified path

The run completed these steps successfully before executing the full test suite:

1. Checked out the exact tested commit.
2. Installed uv 0.13.1 and Python 3.14.8.
3. Synchronized Django 5.2.18, psycopg 3.3.6 and the locked development dependencies.
4. Ran `python manage.py check`: no issues.
5. Connected to `vendor=postgresql`, server version 18.6.
6. Ran `python manage.py makemigrations --check --dry-run`: no drift.
7. Applied all existing migrations to fresh PostgreSQL.
8. Ran Ruff: all checks passed.
9. Ran the full pytest suite: all 115 pre-existing tests passed.

All 58 new Warehouse role cases ended with the explicit expected message:

```text
access_control Warehouse role contract is absent; expected RED until Issue #9 is implemented
```

Final pytest result: `115 passed, 58 errors in 1.42s`. This is a valid behavioral RED because the
runtime, Django configuration, real PostgreSQL connection, migrations, Ruff, test collection and
the complete regression suite succeeded first. No `access_control` application, assignment model,
migration or policy module was present at this commit.

## Covered contract

The RED suite specifies Django's default User identity, the exact persistent field set, four role
values, required and protected references, valid roles, exact-tuple uniqueness, concurrent
duplicate writes, multiple roles and Warehouse assignments, exact primary-key scope across Plant
and Organization boundaries, cross-user isolation, grant revocation, fail-closed inputs, inactive
and anonymous users, no implicit superuser bypass, duplicate-free authorized Warehouse queries and
unusable synthetic passwords.

## Local preparation

Commands ran with synthetic local-check environment values:

```powershell
.\.venv\Scripts\pytest.exe tests\access_control --collect-only -q
.\.venv\Scripts\ruff.exe check .
git diff --check
```

Results: 58 tests collected, Ruff passed, and the diff check reported no content errors. Database
behavior is supported by the GitHub Actions PostgreSQL run above.
