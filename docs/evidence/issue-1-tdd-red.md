# Issue #1 PostgreSQL TDD RED evidence

- Tested commit: [`31ba6be9cf94f50f28267734f7040a4592db3545`](https://github.com/porntaned/ERP-for-Factory/commit/31ba6be9cf94f50f28267734f7040a4592db3545)
- Branch: `feat/warehouse-foundation`
- GitHub Actions run: [Foundation #1](https://github.com/porntaned/ERP-for-Factory/actions/runs/39355731564)
- Environment: GitHub-hosted Ubuntu 24.04 runner with PostgreSQL 18.6 service
- Result: expected RED

## Verified path

The run completed these setup steps successfully before executing the targeted test:

1. Checked out the tested commit.
2. Installed uv 0.13.1 and Python 3.14.8.
3. Synchronized the locked dependencies, including Django 5.2.18 and psycopg 3.3.6.
4. Ran `python manage.py check`: no issues.
5. Opened a real PostgreSQL connection: `vendor=postgresql`, server version 18.6.

Pytest then initialized the database-enabled test session and ran the targeted hierarchy test.
That test failed with the intended missing-behavior message:

```text
facilities.Organization is not registered; expected RED until M2.2 is implemented
1 failed in 0.31s
```

This is a valid behavioral RED because dependency installation, Django configuration, PostgreSQL
startup and connectivity, and test database setup all succeeded first. No `facilities` app,
domain model or migration exists at this commit.

## Local preparation and verification

Commands run from the designated working copy:

```powershell
uv lock
uv sync --locked --all-groups
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\pytest.exe --collect-only -q
.\.venv\Scripts\ruff.exe check .
git diff --check
```

Results: the lock and sync completed, Django reported no issues, pytest collected 43 tests, Ruff
passed and the diff check passed. The behavior tests were not run locally because no local
PostgreSQL server was available; the GitHub Actions run above is the PostgreSQL execution proof.
