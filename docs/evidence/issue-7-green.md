# Issue #7 PostgreSQL GREEN evidence

- Tested commit: [`c66cab65bb0f1dcb7dd1131514446651fecc47cf`](https://github.com/porntaned/ERP-for-Factory/commit/c66cab65bb0f1dcb7dd1131514446651fecc47cf)
- Branch: `feat/lot-identity`
- GitHub Actions run: [Foundation #18](https://github.com/porntaned/ERP-for-Factory/actions/runs/39395440223)
- Job: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39395440223/job/118536913082)
- Environment: Ubuntu 24.04, Python 3.14.8, Django 5.2.18, psycopg 3.3.6 and PostgreSQL 18.6
- Result: GREEN — 115 tests passed in 1.15 seconds

## Verified path

The run checked out the exact implementation commit and completed this path:

1. Installed uv 0.13.1 and Python 3.14.8.
2. Synchronized the locked dependencies.
3. Ran `python manage.py check`: no issues.
4. Connected to `vendor=postgresql`, server version 18.6.
5. Ran `python manage.py makemigrations --check --dry-run`: `No changes detected`.
6. Applied all migrations to fresh PostgreSQL, including `inventory.0001_initial`.
7. Ran Ruff: all checks passed.
8. Ran the full test suite: 115 passed.

## Acceptance evidence

| Issue #7 behavior | Implementation and executed evidence |
| --- | --- |
| Exact minimal schema | `inventory.Lot` has only `id`, `item`, and `code`; schema test locks the concrete fields |
| Required Item and code | Direct NULL writes produce PostgreSQL integrity errors |
| Valid Item reference | Invalid Item FK fails at the PostgreSQL boundary |
| Internal code contract | Regex check plus 1/32 valid and invalid/33-character cases |
| Item-scoped identity | Unique `(item, code)` constraint rejects duplicates and permits the same code for another Item |
| Protected Item | `Lot.item` uses `PROTECT`; deleting a referenced Item raises `ProtectedError` |
| Concurrent duplicates | Two PostgreSQL connections produce one Lot and one `IntegrityError` |
| No duplicated owner | Organization is derived through `lot.item.organization`; no Organization field exists on Lot |

The preceding RED is recorded in [Issue #7 TDD RED evidence](issue-7-tdd-red.md): the 96 existing
tests passed and all 19 Lot cases failed only because `inventory.Lot` was absent.

## Local verification

Commands run with synthetic local-check environment values:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\pytest.exe tests\inventory --collect-only -q
.\.venv\Scripts\ruff.exe check .
git diff --check
```

Results: Django check passed, migration state reported no changes, 19 inventory tests collected,
and Ruff and diff checks passed. Actual database behavior is supported by the GitHub Actions run.
