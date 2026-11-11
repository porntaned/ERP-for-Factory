# M6.4 — QC quantities, concurrency and audit

Repository `porntaned/ERP-for-Factory`; branch `claude/keen-feynman-jkijlw`; base `main` `3b8dac1`.
[Issue #113](https://github.com/porntaned/ERP-for-Factory/issues/113).
Status: **implemented on the branch (2026-11-11); review: none yet; PR not opened** ("spec approved by the owner in chat (2026-11-11); implementation started" and, before it, "spec, awaiting owner approval; no code written" — historical).

Roles (as they actually happen; updated as work proceeds): Manager = the main Claude Code session.
Implementer = a sub-agent spawned by the Manager (started 2026-11-11). Reviewer = a separate Claude Code
session (not started). The owner decides and merges.

## Purpose

M6.1–M6.3 built inspection, the REJECTED rule and tracing. M6.4 closes M6: it proves the QC
commands hold under boundary quantities and concurrent use, and it gives an auditor one place to
see every QC decision.

## Current coverage (traced in `tests/quality/` and code, `main` `3b8dac1`)

- **Quantities:** `test_refusals_write_nothing` refuses an invalid or over-balance `sample_quantity`.
  Not covered as a set: zero, negative, seventh decimal place, 10^14 and above, exactly the balance,
  each in the command and by direct SQL. `record_inspection` reads the balance after locking the Lot
  (`quality/services.py:305`); no test races it against a transfer that lowers the balance.
- **Concurrency:** covered: two inspections (`test_concurrent_inspections_one_wins`), exact retries,
  distinct commands and direct inserts on events, a grant revoked while a transition waits for the
  Lot lock, rejection racing a movement (M6.2). Not covered: two `return_rejected_to_hold` at once;
  a return racing an inspection; a QUALITY grant revoked while `record_inspection` waits; an
  APPROVER grant revoked while `return_rejected_to_hold` waits.
- **Audit:** events and inspections are append-only and attributed (tests exist). There is no place
  to read all QC decisions: the genealogy page shows one Lot. `LotInspection` is not in the admin
  (M6.1 finding 2); `LotDispositionEvent` is, read-only.

## Owner rulings (chat, 2026-11-11)

1. **Audit = tests + a QC history page:** tests prove every decision records who, when, what and
   why and cannot be changed; a read-only page `/quality/audit/` lists every inspection and every
   disposition change, filtered by warehouse and date range, for users with QUALITY or APPROVER at
   that warehouse (as `/quality/`). `LotInspection` joins the read-only admin.
2. **Quantities = sample quantity and balance:** boundaries in the command and in PostgreSQL, and an
   inspection racing a transfer that lowers the balance. Not the m4 performance work.
3. **A bug found by a new test:** fix it in this PR, RED → GREEN, when the fix changes no business
   rule, permission or schema. Otherwise stop and ask the owner.
4. **Open M6.3 items:** accepted as built and not done in M6.4. Finding 5 confirmed: exact,
   case-sensitive Lot search; `lot_positions` reads disposition events in `manufacturing`; a Lot
   reached twice in one level is shown as a repeat. No HOLD caption (finding 3).
5. **Balance limit stays a command rule** (owner, chat 2026-11-11, after the Implementer stopped under
   ruling 3): `record_inspection` refuses a sample above the balance after locking the Lot, as
   designed in M6.1; PostgreSQL checks only the quantity format. No migration. The race test proves
   the command reads the balance under the Lot lock.

## Scope

In: the tests below; the audit page and its nav link; `LotInspection` in the read-only admin; small
fixes under ruling 3; documentation.

Out: M7, m4 (per-row disposition reads on `/quality/` and `/`), M6.3 finding 3, new roles or grants,
schema changes or migrations (a needed one stops for the owner), exports, refactors not needed here.

## Design

### Audit page (`demo`)
- `GET /quality/audit/`, login required; 403 for a user with neither QUALITY nor APPROVER anywhere
  (same rule as `/quality/`). Rows only for warehouses where the user holds QUALITY or APPROVER.
- One table, newest first, of two kinds of row:
  - inspection: time, warehouse, Lot (link to genealogy), kind, result, sample, inspector, note;
  - disposition change: time, warehouse, Lot, from → to, actor, reason, and the inspection it came
    from when there is one.
- Filters (GET): warehouse (only the user's), from-date and to-date (inclusive, local dates). Invalid
  filters show a message, not a 500.
- Read-only: no POST form. A fixed page size with "older" paging, so the query count does not grow
  with history (test with `django_assert_max_num_queries`).
- Nav link "ประวัติ QC" for users who can open it.

### Admin
- `register_read_only(LotInspection)` next to `LotDispositionEvent` (`quality/admin.py`).

## Acceptance criteria and tests (each written first and seen failing, or recorded as a guard that
passed at once because the behaviour already holds)

Quantities (command and direct SQL; the balance limit is a command rule only, see ruling 5):
- `sample_quantity` 0, negative, seven decimal places, 10^14: refused by the command and by direct
  SQL, nothing written; above the balance: refused by the command, nothing written; exactly the
  balance and the smallest valid value (0.000001): accepted.
  (Until 2026-11-11 this line read "0, negative, seven decimal places, 10^14, above the balance:
  refused" under "command and direct SQL", which required a database balance check that M6.1 never
  had — historical, corrected after owner ruling 5.)
- Race: an inspection whose sample equals the balance, and a transfer out of the same pair, in two
  connections. Exactly one order of events wins; never an inspection whose sample exceeds the balance
  at its commit.

Concurrency (two connections, existing `blocked_action` / `wait_for_lock` helpers):
- two `return_rejected_to_hold` with different keys: one event, the other refused;
- return racing an inspection: the chain stays valid (no two events from the same state);
- QUALITY grant revoked while `record_inspection` waits for the Lot lock: refused, nothing written;
- APPROVER grant revoked while `return_rejected_to_hold` waits: refused, nothing written.

Audit:
- every inspection and event carries actor, server time and note or reason; UPDATE and DELETE are
  refused for both (extend the existing tests only where a case is missing);
- page: login required; 403 without QUALITY/APPROVER; only the user's warehouses; both row kinds with
  their fields; newest first; warehouse and date filters, including an invalid date and another
  warehouse's id; Thai text and HTML in a note are escaped; no POST form; query count bounded;
- admin: `LotInspection` listed, view-only (no add, change or delete).

Regression: full suite, Ruff check and format, `makemigrations --check --dry-run` (expect none).

## Documentation (same PR)

- This file: scope delivered, development-check results with the commit they ran on, review status,
  link to the PR's CI comment.
- `docs/reviews/m64-independent-review.md`: review by a separate session.
- `docs/DEVELOPMENT.md`: the audit page on the demo data.
- `docs/assignments/m61-inspection.md`: dated note that finding 2 (admin) was done in M6.4.
- `docs/TASKS.md`, `README.md`: in the post-merge docs PR (M6.4 and M6 ticked), which also records
  the merges of PR #110 (`3b8dac1`) and PR #112 (`a636ff7`) (owner instruction, chat 2026-11-11).

## Process

Implementer: a sub-agent, test-first, on this branch. Reviewer: a separate session given only the PR
number, the Issue number and this path; it takes no further work on the slice after its report
(`docs/MULTI_AGENT.md`). Repair: at most 2 rounds. Local runs are development checks; CI on
PostgreSQL 18.6 is the evidence of record, cited by link while the PR is open. The owner merges or
tells the Manager to; the Manager opens the post-merge docs PR.

## Decisions taken by the Manager (for approval with this spec)

1. One combined, newest-first table rather than two tabs.
2. Fixed page size with "older" paging (bounded queries).
3. Date filters as inclusive local dates.
4. Race tests reuse the existing two-connection helpers.

## Evidence (Implementer, 2026-11-11)

Review so far: **none** (no self-review is claimed as review; no independent review yet). CI on
PostgreSQL 18.6 is the evidence of record and is cited here by link to the PR's CI comment once the
PR exists. The results below are development checks.

### Scope delivered

- Tests: `tests/quality/test_qc_hardening.py` (quantities, concurrency, audit records),
  `tests/web/test_quality_audit.py` (audit page), `tests/web/test_quality_admin.py` (admin).
- Audit page: `GET /quality/audit/` (`quality-audit`) in `demo/quality_views.py`
  (`quality_audit`, `AUDIT_PAGE_SIZE = 50`), `demo/quality_forms.py` (`AuditFilterForm`),
  `demo/templates/demo/quality/audit.html`, route in `config/urls.py`, nav link "ประวัติ QC" in
  `demo/templates/demo/base.html` (shown with "คุณภาพ", same rule).
- Admin: `register_read_only(LotDispositionEvent, LotInspection)` in `quality/admin.py`.
- No change to `quality/services.py`, models, migrations, roles or grants. No new dependency.

### Test groups: RED / GREEN or guard

| Group | Tests | Result first run | Why |
|---|---|---|---|
| Quantities | command refuses 0, -1, -0.000001, 0.0000001, 1.0000001, 10^14, 10^14+1 (format message) and 10.000001, 11 above a balance of 10 (balance message); accepts 10, 10.000000, 0.000001; raw SQL `INSERT` refuses the same format set with `inspection_sample_quantity_valid` and accepts 10, 0.000001, 99999999999999.999999; two balance races | **guard (passed at once)**, 24 tests | `is_valid_quantity`, the balance read after the Lot lock and the check constraint already hold. Checked against deliberate breaks, not committed: without the command's format and balance checks 10 tests fail; reading the balance before the Lot lock fails the reversal race; with the check constraint dropped the SQL tests fail with "DID NOT RAISE" |
| Concurrency | two returns with different keys; return racing an inspection (3 orders); QUALITY grant revoked while `record_inspection` waits; APPROVER grant revoked while `return_rejected_to_hold` waits | **guard (passed at once)**, 6 tests | Every command locks the Lot first and reads state and grants after it. Checked: reading the return's state before the Lot lock, or checking the QUALITY grant before it, fails 3 of them |
| Audit records | actor, server time and note or reason on every inspection and event a command records (PASS, RELEASED→HOLD, FAIL, REJECTED→HOLD); a direct insert cannot choose its time; UPDATE of inspector, time, result, sample, actor, target state, inspection link refused as append-only | **guard (passed at once)**, 10 tests | The insert triggers set `created_at := statement_timestamp()` and the append-only triggers refuse UPDATE/DELETE. Checked: with the user triggers disabled, the time test and UPDATE tests fail. UPDATE of note/reason and DELETE were already covered (`test_inspection.py`, `test_postgresql_constraints.py`) and are not repeated |
| Audit page | login; 403 without QUALITY/APPROVER and no nav link; only the user's warehouses (also in the filter choices); both row kinds with their fields; an event without inspection; newest first; warehouse filter; another warehouse's id, unknown and non-numeric ids; inclusive local dates (rows placed at 00:30 and 23:59:59 local and at the next local midnight); invalid dates, from after to, bad page numbers; extreme valid dates; Thai text and HTML escaped; no POST form, POST → 405; "older" paging walks every row once; query count | **RED → GREEN**, 23 tests | RED on `28ec20b`: 404, the route did not exist. GREEN after the view, form, template, route and nav link |
| Admin | `LotInspection` listed and viewable; add, change POST, delete and the bulk delete action refused | **RED → GREEN**, 1 test | RED on `28ec20b`: not listed in the admin. GREEN after `register_read_only` |

The RED run of the page and admin tests was repeated on a clean worktree of `28ec20b` with only the
two new test files: 24 failed.

### Rulings made while building (Implementer; for the Reviewer and owner to check)

1. **Balance race.** A transfer out of a HOLD Lot-Warehouse is refused by the RELEASED gate at its
   source, so a transfer can only follow an inspection, never precede it.
   `test_inspection_of_the_whole_balance_then_a_transfer_out` checks that order (the transfer waits
   for the inspection's Lot lock, then commits; the inspection's sample equals the balance at its
   commit) and that the transfer cannot go first. The other order uses a **receipt reversal**, the
   movement that lowers a HOLD balance (`reverse_receipt`, Quality irrelevant):
   `test_balance_lowered_first_then_the_waiting_inspection_is_refused`. Inspecting at the line was
   not used, because M6.2 ruling Q2 says a Lot at the line is not inspected again.
2. **"Above the balance … direct SQL".** PostgreSQL has no balance check on an inspection; the
   balance is the command's rule (M6.1, and `tests/quality/helpers.force_release` depends on it for
   setups without stock, owner ruling 2026-11-06). Adding one would need a migration and change a
   rule, so under ruling 3 it was **not** added and no test asserts either way. **Open for the
   owner.** The direct-SQL tests cover the format bounds only.
3. Page details: one combined table (`inspection` / `event` rows); a row's "การตรวจ" column shows the
   inspection number, on the inspection and on the event it produced. Invalid filters (including a
   warehouse the user may not see) show "ตัวกรองไม่ถูกต้อง: …" and **no rows**, rather than falling
   back to all warehouses. "ตั้งแต่วันที่" after "ถึงวันที่" is invalid. The page number is limited to
   1–1,000,000. Dates use the `__date` lookup in `TIME_ZONE` (Asia/Bangkok), so `date.max` cannot
   overflow. Paging is by page number (offset); rows added between two page loads can shift a row
   to the next page (read-only, accepted). Nav link shown wherever "คุณภาพ" is.
4. The date-filter test moves three synthetic rows to chosen times with the append-only triggers
   disabled **inside that test's transaction only** (rolled back); no production code path changes
   them.

### Bugs found

None in existing code. While making the page test GREEN, the warehouse filter first listed
"Warehouse object (n)" (the model has no `__str__`); the tightened test now requires the choices
`["ทุกคลัง", "FG"]` and the form labels choices by code.

### Development checks (not evidence of record)

Environment: PostgreSQL 16.15 (local cluster), Python 3.14.6, Django 5.2.18. Code commit
`d25f2da` (docs commits after it change no code).

- `UV_PYTHON=3.14 uv run --env-file .env pytest -q` → **1160 passed** (base `main` `3b8dac1`:
  1096; +64 new: 40 + 23 + 1).
- `uv run ruff check .` → All checks passed; `uv run ruff format --check .` → 269 files already
  formatted.
- `python manage.py makemigrations --check --dry-run` → No changes detected.
- `seed_production_demo --reset`, then `/quality/audit/` through the Django test client:
  `demo-quality` 200, 14 rows (7 inspections, 7 events) at RM-A and FG; `demo-approver` 200, the
  same 14 rows; `demo-warehouse` 403; `?warehouse=<FG>` 2 rows; `?date_from=2026-13-01` 200 with
  the message.
- Query count of the page: 10 queries with the seeded history and with 120 more rows
  (`test_query_count_does_not_grow_with_history`, bound 12).

### Review and CI

- Review: none yet. The Reviewer (separate session) writes `docs/reviews/m64-independent-review.md`.
- CI: cited by link to the PR's CI comment once the PR exists (AGENTS.md → Verification).
