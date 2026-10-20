# Issue #7 PostgreSQL TDD RED evidence

- Tested commit: [`dab4b460bb5f0fea476a72d8c609746e02c708d1`](https://github.com/porntaned/ERP-for-Factory/commit/dab4b460bb5f0fea476a72d8c609746e02c708d1)
- Branch: `feat/lot-identity`
- GitHub Actions run: [Foundation #16](https://github.com/porntaned/ERP-for-Factory/actions/runs/39394726202)
- Job: [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/39394726202/job/118534505278)
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
9. Ran the full pytest suite: all 96 pre-existing tests passed.

All 19 new Lot cases failed with the explicit expected message:

```text
inventory.Lot is not registered; expected RED until Issue #7 is implemented
```

Final pytest result: `19 failed, 96 passed in 1.02s`. This is a valid behavioral RED because the
runtime, Django configuration, real PostgreSQL connection, migrations, Ruff, test collection and
the complete regression suite succeeded first. No `inventory` application, model or migration was
present at this commit.

## Covered contract

The RED suite specifies the exact persistent field set (`id`, `item`, `code`), Item protection,
required fields, invalid Item references, the 1–32-character internal code contract, Item-scoped
uniqueness, reuse of a code for a different Item and concurrent duplicate writes.

## Local preparation

Commands run with synthetic local-check environment values:

```powershell
.\.venv\Scripts\pytest.exe tests\inventory --collect-only -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe manage.py check
git diff --check
```

Results: 19 tests collected, Ruff and Django checks passed, and the diff check reported no errors.
Database behavior is supported by the GitHub Actions PostgreSQL run above.
