# Development and test environment

## Version contract

The first issue uses exact versions so local and CI evidence can be reproduced:

- Python 3.14.8
- Django 5.2.18 LTS
- PostgreSQL 18.6
- psycopg 3.3.6 with the binary extra
- pytest 9.1.1
- pytest-django 4.14.0
- Ruff 0.17.1
- uv 0.13.1 in CI

The version choices follow the supported Django 5.2 LTS line, the current Python 3.14
maintenance release and the current PostgreSQL 18 minor release as of 2026-10-19. Update an
exact pin only in a separate reviewed change with the relevant checks rerun.

Primary version references:

- [Python 3.14.8 release](https://www.python.org/downloads/release/python-3148/)
- [Django supported versions](https://www.djangoproject.com/download/)
- [Django 5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [Psycopg installation support](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [uv 0.13.1 release](https://github.com/astral-sh/uv/releases/tag/0.13.1)

## Configuration boundary

`config.settings` requires the secret key and every PostgreSQL connection value from environment
variables. Copy `.env.example` to `.env`, replace every placeholder and keep `.env` outside Git.
The repository contains no development or CI credentials. GitHub Actions uses synthetic job-only
values and a disposable PostgreSQL service.

Required variables:

- `DJANGO_SECRET_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

`DJANGO_DEBUG` is optional and defaults to `false`.

## Local commands

Local PostgreSQL 18.6 must already be reachable using the values in `.env`.

```powershell
Copy-Item .env.example .env
# Replace every placeholder in .env before continuing.
uv sync --locked --all-groups
uv run --env-file .env python manage.py check
uv run --env-file .env pytest
uv run ruff check .
```

SQLite is deliberately unsupported because it cannot prove the PostgreSQL constraints or
concurrency behavior required by Issue #1.

## Inventory demo walkthrough (M4.7)

Use a disposable database: `seed_demo --reset` flushes every table.

```bash
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py seed_demo --reset   # receives 100 of L-0001 at RM-A, RELEASED
uv run --env-file .env python manage.py set_demo_passwords  # prompts for a password (min 8 chars)
DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver
```

1. Open `http://127.0.0.1:8000/accounts/login/` and log in as `demo-warehouse`.
2. The balance page shows `L-0001 · RM-A · 100 · RELEASED`.
3. **โอน**: lot `L-0001`, source `RM-A`, destination `RM-B`, quantity `30`, any reason → **บันทึกการโอน**.
4. The balance page shows `RM-A 70 RELEASED` and `RM-B 30 HOLD` (the destination keeps its own
   Quality state, M4.3.3).
5. **ประวัติ** lists receipt `R1` (+100) and transfer `T1` (RM-A → RM-B, 30). Reverse buttons
   appear only for `demo-approver`.

`tests/web/test_m47_demo.py` runs the same steps through HTTP on PostgreSQL. Screenshots:
`docs/evidence/m47/`.

## Evidence rule

CI (PostgreSQL 18.6, Python 3.14.8) is the evidence of record. Each run posts a summary with
the commit SHA, server version and test counts as a commit comment, and keeps one updated
comment on the PR, written by `scripts/ci_summary.py`. A local run on a different PostgreSQL
or Python version is a development check, not evidence.

`ruff format --check .` runs in CI; run `uv run ruff format .` before committing.

A TDD RED result is valid only after dependency installation, Django settings, PostgreSQL
connectivity and test database creation succeed. Import errors, missing environment variables,
database connection failures, migration errors and SQLite runs are environment failures rather
than business-behavior evidence.
