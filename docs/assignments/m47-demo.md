# M4.7 — demo: receive 100 → transfer 30 → 70 / 30

Repository `porntaned/ERP-for-Factory`; branch `claude/dreamy-volta-9v3i8u`; base `main`
`d1dd0bc`. [Issue #66](https://github.com/porntaned/ERP-for-Factory/issues/66). The owner approved
the scope and the evidence approach (HTTP test in CI + local screenshots, no new dependency) in
chat on 2026-11-04.

## Scope

- End-to-end test through the screens on PostgreSQL: `seed_demo` → login with a password set by
  `set_demo_passwords` → transfer form → post 30 with the form's own request UUID → balance page
  70 / 30 → history page; a double submit replays; ledger holds exactly +100, −30, +30.
- Step-by-step walkthrough in `docs/DEVELOPMENT.md` and screenshots in `docs/evidence/m47/`.

Excluded: business rules, schema, migrations, triggers, new dependencies, Deploy, M5–M7.

## Defect found by the demo and fixed

The balance page, history and success messages displayed quantities with
`Decimal.normalize()`, which renders whole numbers ending in zero in scientific notation:
30 → `3E+1`, 100 → `1E+2`, 70 → `7E+1`. Earlier screen tests used 25, so they never hit it.
Fix: `demo/quantities.py` `format_quantity` (`f"{value.normalize():f}"`) and a `quantity`
template filter, used in `demo/views.py` and `history.html`. Display only; the stored values and
the Inventory commands are unchanged.

## RED / GREEN

- RED: `test_demo_receive_100_transfer_30_shows_70_and_30` failed at the success message
  assertion because the page showed `3E+1` rather than `30`.
- GREEN after the fix, plus 7 parametrized `format_quantity` cases (30, 100, 70.000, −30, 2.500,
  0.001, 0).

## Verification (development check, not evidence of record)

Environment: PostgreSQL 16.15 (Ubuntu), Python 3.14.6 via `UV_PYTHON=3.14.6` (3.14.8 is not
available in this session), tested commit `838a90d9c308124f87b4c72b19d4503c8a0c4700`.

| Command | Result |
|---|---|
| `uv run pytest -q tests/web` | 36 passed |
| `uv run pytest -q` | 759 passed |
| `uv run ruff check .` / `uv run ruff format --check .` | clean |
| `uv run python manage.py makemigrations --check --dry-run` | No changes detected |

Real server on a scratch database: `migrate` → `seed_demo --reset` →
`set_demo_passwords --password-stdin` → `runserver`; Playwright (pre-installed in the session,
not a project dependency) logged in as `demo-warehouse`, filled the transfer form and captured
the four screenshots. Server log: one `POST /transfers/new/` → 302, no 5xx. The sandbox cannot
reach `cdn.jsdelivr.net`, so the screenshot script served the same Bootstrap 5.3.3
`bootstrap.min.css` from the npm package tarball (sha256 `3c8f27e6…6fc8`) for that one URL.

Screenshots: [before](../evidence/m47/1-before-100-at-rm-a.png),
[transfer form](../evidence/m47/2-transfer-form-30.png),
[after 70 / 30](../evidence/m47/3-after-70-and-30.png), [history](../evidence/m47/4-history.png).

CI evidence of record: the CI comment on the PR.

## Review

Self-review only, following `docs/SCRUTINIZE.md`. No schema, trigger or migration change.

Self-review trace (SCRUTINIZE): every display of a quantity in `demo/` was found with
`grep -rn normalize demo inventory quality` (balance page, receipt and transfer success messages,
history receipt and transfer rows); all four now go through `format_quantity`, and no
`normalize` display remains. Zero (a fully reversed balance), negative deltas and fractional
quantities are covered by the parametrized test. The E2E test uses only the login page, the
transfer form and `seed_demo`; no helper writes stock. Smaller alternative considered: a test
with force_login and a hard-coded UUID; rejected because it would not prove the login page or the
form's own request UUID. Verdict: `ship`.
