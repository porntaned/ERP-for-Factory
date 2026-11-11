# M6.4 — QC quantities, concurrency and audit

Repository `porntaned/ERP-for-Factory`; branch `claude/keen-feynman-jkijlw`; base `main` `3b8dac1`.
[Issue #113](https://github.com/porntaned/ERP-for-Factory/issues/113).
Status: **spec approved by the owner in chat (2026-11-11); implementation started** ("spec, awaiting owner approval; no code written" held until then — historical).

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

Quantities (command and direct SQL):
- `sample_quantity` 0, negative, seven decimal places, 10^14, above the balance: refused, nothing
  written; exactly the balance and the smallest valid value (0.000001): accepted.
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
