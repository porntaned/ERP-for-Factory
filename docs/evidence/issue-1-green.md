# Issue #1 PostgreSQL GREEN evidence

- Tested commit: [`8fdb446669c47f892774c2fba2c2093ba4d1c1e8`](https://github.com/porntaned/ERP-for-Factory/commit/8fdb446669c47f892774c2fba2c2093ba4d1c1e8)
- Branch: `feat/warehouse-foundation`
- GitHub Actions run: [Foundation #4](https://github.com/porntaned/ERP-for-Factory/actions/runs/39369435238)
- Environment: GitHub-hosted Ubuntu 24.04 runner with PostgreSQL 18.6
- Result: GREEN — 51 tests passed in 0.58 seconds

## Verified path

The run checked out the exact commit above and completed the following path:

1. Installed uv 0.13.1 and Python 3.14.8.
2. Synchronized the lock file with Django 5.2.18 and psycopg 3.3.6.
3. Ran `python manage.py check`: no issues.
4. Opened a real database connection and reported `vendor=postgresql`, server version 18.6.
5. Ran `python manage.py makemigrations --check --dry-run`: no model or migration drift.
6. Applied `facilities.0001_initial` to a fresh PostgreSQL database.
7. Ran Ruff: all checks passed.
8. Ran the complete test suite: 51 tests passed.

## Acceptance evidence

| Issue #1 behavior | Implementation and executed evidence |
| --- | --- |
| Organization → Plant → Warehouse hierarchy | Foreign keys in `facilities/models.py`; creation path exercised in `tests/foundation/test_hierarchy.py` |
| Required fields | Database NOT NULL constraints; eight direct `NULL` cases in `tests/foundation/test_postgresql_constraints.py` |
| Global Organization code uniqueness | Unique field plus duplicate-write test |
| Plant code unique within Organization | Scoped unique constraint plus same-parent and different-parent cases |
| Warehouse code unique within Plant | Scoped unique constraint plus same-parent, different-parent and concurrent-write cases |
| Code format and boundaries | Database check constraints plus empty, Unicode, invalid-character, length and valid-boundary cases |
| Invalid parents | Direct database writes with nonexistent parent IDs for Plant and Warehouse |
| Deletion protection | Separate Organization → Plant and Plant → Warehouse graphs verify `PROTECT` |
| Thai display names | Valid Thai text is stored and read back unchanged |
| Concurrent duplicate writes | Two independent PostgreSQL connections produce one insert and one `IntegrityError` |

The preceding RED is recorded in [`issue-1-tdd-red.md`](issue-1-tdd-red.md). It failed because
the facilities models did not exist after the environment and PostgreSQL connection had passed.

## Local verification

Commands run from the designated working copy after setting the six required environment
variables to synthetic local-check values:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe --collect-only -q
git diff --check
```

Results: Django check, Ruff and diff check passed; the migration command reported no changes and
warned that a local PostgreSQL connection was unavailable; pytest collected all 51 tests. The
behavior suite was therefore executed only in the GitHub Actions PostgreSQL environment above.
