# M4.6 — receipt, transfer, history and reversal screens

Repository `porntaned/ERP-for-Factory`; branch `codex/web/m46-inventory-screens`; base `main`
`125bc104ead8d0dc0d7ef0a809d62252ae7c8fea`. [Issue #63](https://github.com/porntaned/ERP-for-Factory/issues/63). Owner approved on
2026-11-04 and asked for M4.6 end to end, including merge.

## Owner decisions

- Demo passwords are set by a local command; nothing is stored in the repository.
- Screens are permission-aware; the Inventory commands still enforce authority.

## Delivered

- Login/logout for ordinary users (`/accounts/login/`, POST `/accounts/logout/`); `LOGIN_URL`
  moved from the staff-only admin login.
- `manage.py set_demo_passwords [--password-stdin]` (minimum 8 characters) for `demo-*` users;
  `seed_demo` adds `demo-approver` (APPROVER at RM-A, RM-B).
- `/receipts/new/` (warehouses with WAREHOUSE only), `/transfers/new/` (WAREHOUSE at both
  ends, distinct warehouses), `/history/` (receipts, transfers, reversals) with reverse forms
  only for APPROVER at every involved warehouse and not yet reversed; POST-only reversal URLs
  return 403 without that authority. Navigation uses `access_control.policies`, its first use
  outside tests.
- A hidden request UUID per form: a double submit replays instead of posting twice. Command
  errors (insufficient stock, Quality gate, authority, already reversed, key conflict) become
  messages and write nothing.
- CI step for `tests/web`.

## RED / GREEN

18 of the new screen tests failed first (404 for missing pages, missing command and
`demo-approver`), then GREEN. A real-server smoke run found choice labels rendered as
`Lot object (1)`; fixed with readable labels and a regression test.

## Verification

- Local (development check, PostgreSQL 16.15 / Python 3.14.6): full suite 750 passed before the
  label fix, web suite 28 passed after; Ruff check/format and `makemigrations --check` clean.
- Real server on a scratch DB: `migrate` → `seed_demo` → `set_demo_passwords --password-stdin`
  → `runserver`; login as `demo-warehouse` (302), two POSTs of one transfer form with the same
  request UUID → one transfer, balances RM-A 70 / RM-B 30; `demo-approver` sees 2 reverse forms
  and no receipt link; no 500 responses in the server log.
- CI evidence of record: the CI comment on the PR.

## Review

Self-review only. No schema, trigger or migration change, so no independent review (agreed
2026-11-04 to save quota).
