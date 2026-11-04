# Web scaffold and synthetic demo data (prep for M4.6, delivers M7.1)

Repository `porntaned/ERP-for-Factory`; branch `codex/web/scaffold-demo`; base `main` `32ca3d2`.
[Issue #54](https://github.com/porntaned/ERP-for-Factory/issues/54), [PR #55](https://github.com/porntaned/ERP-for-Factory/pull/55). Owner approved on 2026-11-04.

## Scope delivered

- Django web stack (admin, sessions, messages, staticfiles, middleware, URLs, templates, WSGI);
  `DJANGO_ALLOWED_HOSTS` defaulting to localhost.
- `/`: login-only, read-only balance and Quality disposition per Lot–Warehouse.
- Admin: every domain model visible; add/change/delete refused (`config/readonly_admin.py`).
- `manage.py seed_demo [--reset]`: synthetic LEDCO / P1 / RM-A, RM-B, FG, items, lot L-0001,
  demo users with unusable passwords; receipt of 100 at RM-A and Quality release via the real
  commands with fixed request UUIDs, so a rerun replays. `--reset` flushes the whole database.

Excluded: receipt/transfer screens (M4.6), transfer demo (M4.7), writes through web/admin,
credentials in the repo, deployment.

## Verification

- Tests `tests/web/test_scaffold.py` (9), written alongside the code, not RED-first.
- Local (development only): PostgreSQL 16.15, Python 3.14.6; full suite 665 passed; Ruff,
  `manage.py check`, `makemigrations --check` clean. Smoke on a scratch DB: `migrate` →
  `seed_demo` → `runserver`; `GET /` → 302 to `/admin/login/?next=/`, `GET /admin/login/` → 200.
- Self-review only; no independent review.

## Closeout (2026-11-04)

Owner approved merge; PR #55 merged at `a21208df84f7b3b594d423b9f6d77573a05cd21e`, main CI #165
success; final main `45df3cc` CI #166 success (step conclusions only). Issue #54 closed.
