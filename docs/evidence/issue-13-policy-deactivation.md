# Issue #13 — PostgreSQL evidence

Scope: audit Finding 1 only, on branch `codex/fix-policy-deactivation` from main
`9b1d182eb6867b70f076e95a63dc03f1814f00ec`. Manager `/root` inspected CI logs;
this is self-verification, separate from the independent review.

## RED

- Commit: `b332c10560af86e46f6e11347e4456735c4aee11`.
- [Run](https://github.com/porntaned/ERP-for-Factory/actions/runs/39565893323),
  [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39565893323/job/119107957640).
- `uv run pytest -q --tb=short`: **3 failed, 261 passed in 4.55s**.
- Failures: all three tests in `tests/access_control/test_persisted_deactivation.py`.
  The boolean policy returned True, the fresh warehouse query returned a warehouse,
  and a query built before deactivation still returned that warehouse when evaluated.
- Each test first proved authorized access for the same active saved user and grant.
  A separate ORM UPDATE deactivated the row while the retained instance stayed active.
- Configuration, migration drift, fresh migrations and Ruff passed.

## GREEN

- Implementation commit: `abe63e154de62e7d37f3ff4c47252f6a88c07587`.
- [Run](https://github.com/porntaned/ERP-for-Factory/actions/runs/39566040200),
  [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39566040200/job/119108431491).
- Targeted module: **3 passed in 0.46s**.
- Full suite: **264 passed in 3.27s**.
- Django checks: no issues; migration drift: no changes; fresh migrations and Ruff passed.
- Production diff: only `user__is_active=True` and `role_assignments__user__is_active=True`
  in the existing policy queries. No schema changes or added dependencies.

## Runtime and commands

GitHub-hosted Ubuntu 24.04; Python 3.14.8; Django 5.2.18; psycopg 3.3.6;
PostgreSQL `18.6 (Debian 18.6-1.pgdg12+2)` (vendor and server version checked in CI).

```text
uv sync --locked --all-groups
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run ruff check .
uv run pytest -q --tb=short
```

GREEN workflow additionally runs the targeted module before the full suite:
`uv run pytest -q tests/access_control/test_persisted_deactivation.py --tb=short`.
The exact PostgreSQL connection/version command is in `.github/workflows/foundation.yml`.
Local `.venv/Scripts/ruff.exe check .` and `git diff --check` passed; local checks are not PostgreSQL evidence.

## Boundary

The change reads persisted active state in the same SQL statement as the grant check.
It preserves the existing fail-closed in-memory guard, role matching, warehouse isolation
and distinct results. QuerySet construction remains lazy. Already-evaluated QuerySets
retain Django's result cache; callers must issue a fresh policy query for a fresh decision.
A policy read is not a transaction lock spanning a later write. Quality's write command
already reloads and locks its actor/grant and is unchanged.

Findings 2–5 remain outstanding. Their reproductions remain on the separate audit branch;
none was removed or skipped from main to make this branch GREEN.
