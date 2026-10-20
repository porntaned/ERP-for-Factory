# Issue #5 PostgreSQL GREEN evidence

- Tested commit: [`05b7effe3eaba8a3b60b04aeee4542bd747c9308`](https://github.com/porntaned/ERP-for-Factory/commit/05b7effe3eaba8a3b60b04aeee4542bd747c9308)
- Branch: `feat/item-uom-foundation`
- GitHub Actions run: [Foundation #11](https://github.com/porntaned/ERP-for-Factory/actions/runs/39390768062)
- Job: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39390768062/job/118521455777)
- Environment: Ubuntu 24.04, Python 3.14.8, Django 5.2.18, psycopg 3.3.6 and PostgreSQL 18.6
- Result: GREEN — 96 tests passed in 0.63 seconds

## Verified path

The run checked out the exact tested commit and completed this path:

1. Installed uv 0.13.1 and Python 3.14.8.
2. Synchronized the locked dependencies.
3. Ran `python manage.py check`: no issues.
4. Connected to `vendor=postgresql`, server version 18.6.
5. Ran `python manage.py makemigrations --check --dry-run`: `No changes detected`.
6. Applied all migrations to fresh PostgreSQL, including `catalog.0001_initial`.
7. Ran Ruff: all checks passed.
8. Ran the full test suite: 96 passed.

## Acceptance evidence

| Issue #5 behavior | Implementation and executed evidence |
| --- | --- |
| Global Unit of Measure | `catalog.UnitOfMeasure`; global unique code test |
| Organization-owned Item | `Item.organization` uses `PROTECT`; creation and invalid-FK tests |
| Protected base UOM | `Item.base_uom` uses `PROTECT`; deletion and invalid-FK tests |
| Scoped Item code | Unique constraint on `(organization, code)`; same/different Organization cases |
| Uppercase code contract | Database regex checks for both models; invalid and 1/32-character boundary cases |
| Item types | `RAW`, `WIP`, `FINISHED` choices plus database CHECK and invalid-value tests |
| Required data | Direct NULL writes for all required fields produce database errors |
| Unicode and documented empty names | Thai text round-trip plus explicit empty-name persistence cases |
| Concurrent duplicate writes | Two PostgreSQL connections produce one Item and one `IntegrityError` |

The preceding RED is recorded in [Issue #5 TDD RED evidence](issue-5-tdd-red.md). It passed the
existing 51 tests and failed all 45 catalog cases because the catalog models were absent.

## Local verification

Commands run with synthetic local-check environment values:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\pytest.exe --collect-only -q
.\.venv\Scripts\ruff.exe check .
git diff --check
```

Results: Django check passed, migration state reported no changes, 96 tests collected, Ruff and
diff checks passed. The local PostgreSQL port was unavailable, so actual database behavior is
supported by the GitHub Actions run above.
