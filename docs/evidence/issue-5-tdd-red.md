# Issue #5 PostgreSQL TDD RED evidence

- Tested commit: [`ca4dacbdc349ff7b4fcf5a3be10035c02e6f2c28`](https://github.com/porntaned/ERP-for-Factory/commit/ca4dacbdc349ff7b4fcf5a3be10035c02e6f2c28)
- Branch: `feat/item-uom-foundation`
- GitHub Actions run: [Foundation #8](https://github.com/porntaned/ERP-for-Factory/actions/runs/39389877487)
- Job: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39389877487/job/118518530320)
- Environment: GitHub-hosted Ubuntu 24.04 runner with PostgreSQL 18.6
- Result: expected RED

## Verified path

The run completed these steps successfully before executing the full test suite:

1. Checked out the exact tested commit.
2. Installed uv 0.13.1 and Python 3.14.8.
3. Synchronized the locked dependencies, including Django 5.2.18 and psycopg 3.3.6.
4. Ran `python manage.py check`: no issues.
5. Opened a real database connection: `vendor=postgresql`, server version 18.6.
6. Ran `python manage.py makemigrations --check --dry-run`: no drift.
7. Applied the existing migrations to fresh PostgreSQL.
8. Ran Ruff: all checks passed.
9. Ran the complete pytest suite: all 51 pre-existing foundation tests passed.

The new catalog tests then failed only because the new application and models had not been
implemented. The repeated explicit failure was:

```text
catalog.UnitOfMeasure is not registered; expected RED until Issue #5 is implemented
```

Final pytest result: `11 failed, 51 passed, 32 errors in 0.65s`. The failures and setup errors are
the 43 new catalog cases; the 51 existing tests remained GREEN. This is a valid behavioral RED
because dependencies, Django configuration, PostgreSQL startup and connection, migrations, Ruff,
test collection and the existing regression suite succeeded first.

## Local preparation

Commands run from the designated working copy with synthetic local-check environment values:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\pytest.exe --collect-only -q
.\.venv\Scripts\ruff.exe check .
git diff --check
```

Results: Django reported no issues, pytest collected 94 tests, Ruff passed and the diff check
passed. Database behavior was executed by the GitHub Actions PostgreSQL environment above.
