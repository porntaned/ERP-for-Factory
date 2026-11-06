# M6.2 — Hold/Release enforced with Inventory

Repository `porntaned/ERP-for-Factory`; branch `claude/keen-feynman-jkijlw`; base `main` `96d15f9`.
[Issue #103](https://github.com/porntaned/ERP-for-Factory/issues/103).
Status: **implemented; [PR #104](https://github.com/porntaned/ERP-for-Factory/pull/104) open; independent review done (fix-then-ship, repair round 1 of 2 applied, docs only); CI on PostgreSQL 18.6 pending at the time of writing; awaiting the owner** (2026-11-06).
("implemented on the branch; review so far: none ... no pull request exists yet ... CI has not run" held until the PR was opened and reviewed — historical.)
("spec approved by the owner in chat (2026-11-06); implementation started" held until then — historical.)

Roles in this slice (as they actually happened): Manager = the main Claude Code session (scope, spec, PR, verification
re-run, review record). Implementer = sub-agent spawned by the Manager (wrote the code, tests and the evidence below).
Reviewer = a separate Claude Code session (`session_01MVmjhbsKYvC1RZ5mHmggzs`) created by the Manager; it received only the PR
number, the Issue number and this path. Owner decides and merges.

## Purpose

Inventory checks a Lot's disposition per warehouse and only on some commands. A Lot that is
REJECTED at one warehouse can still be moved, issued and consumed from another. The owner ruled
at the M5.2 scrutinize: **a REJECTED Lot may not be used at any warehouse, but it may still be
scrapped.** M6.2 enforces that in the commands and in PostgreSQL.

## Current behaviour (traced in code, `main` `96d15f9`)

| Command | Disposition check today | Where |
|---|---|---|
| `transfer_stock` | source must be RELEASED; destination unchecked | `inventory/transfers.py:181` |
| `issue_material` | source warehouse must be RELEASED; line unchecked | `post_production_transfer`, `quality_at_source=True` |
| `return_material` | destination warehouse must be RELEASED; line unchecked | same, `quality_at_source=False` |
| `reverse_transfer` | the original destination (where goods leave) must be RELEASED; the returning side unchecked | `inventory/reversals.py:193` |
| `receive_stock`, `reverse_receipt` | none (M4.5: "any Quality state") | `inventory/services.py`, `reversals.py` |
| CONSUME, OUTPUT | none | `inventory/production.py` |
| SCRAP, `reverse_production_posting` | none | `inventory/production.py` |

PostgreSQL has **no** rule in `inventory` that reads a disposition: every gate above is in a
command, and a direct INSERT into `inventory_stockledgerentry` passes.

## Owner rulings (chat, 2026-11-06)

1. **Q1 — the rule.** While a Lot is REJECTED at **any** warehouse of its organization:
   - refused: transfer (either side), issue, return, CONSUME, further receipt, further OUTPUT,
     reversal of a transfer, reversal of a CONSUME, reversal of a SCRAP;
   - still allowed (they only take stock out): SCRAP, reversal of a receipt, reversal of an
     OUTPUT.
2. **Q2 — HOLD at the line.** A Lot issued to a line stays HOLD there (a new pair starts at HOLD)
   and is **not** inspected again. The RELEASED gate at the issue source is the inspection.
   CONSUME needs only that the Lot is not REJECTED anywhere.
3. **Q3 — REJECTED while an order holds the Lot.** The order is **frozen** for that Lot: rule 1
   applies to it. The only way to clear the line is SCRAP by an APPROVER (existing authority).
   Nothing happens automatically. Closing an order still needs an empty line (existing rule, not
   changed). Quantity already consumed is not touched.
4. **Q4 — inspecting elsewhere.** `record_inspection` is unchanged. A Lot REJECTED at A can still be
   inspected at B and RELEASED there; that result is recorded, but the Lot stays unusable until it
   is no longer REJECTED anywhere.
5. No new role, no demo grant change, no automatic stock adjustment (AGENTS.md: owner approval).

## Scope

In:
- the rule above in each command listed, and in PostgreSQL;
- screens that call these commands show a message, not a 500;
- tests (RED first), migration, documentation.

Out: M6.3 and M6.4, M7, scrap/return to supplier, checklists, valuation, Deploy, m4 (performance of
`/quality/`), refactors not needed for this slice (noted in the final report instead).

## Design

### Definition
A Lot is **blocked** when, for at least one warehouse, the latest `LotDispositionEvent` for that
Lot and warehouse has `to_disposition = REJECTED`. Leaving REJECTED (REJECTED → HOLD by an
APPROVER, M6.1) unblocks it. "Latest" is whatever `quality.services.get_lot_disposition` uses.
Quality owns this reading; Inventory enforces it (AGENTS.md domain ownership).

### Commands
- `quality.services`: a read-only function that returns the warehouses where a Lot is REJECTED.
- `inventory`: one gate helper, called inside each command **after** the Lot lock and **after** the
  exact-replay check, before any write. It raises a new `LotRejectedError`.
  - Called by: `_post_transfer` (so transfer, issue and return), `receive_stock`,
    `post_production_posting` for CONSUME and OUTPUT (not SCRAP), `reverse_transfer`, and
    `reverse_production_posting` when the original is CONSUME or SCRAP (not OUTPUT).
  - Not called by: SCRAP, `reverse_receipt`, `reverse_production_posting` of an OUTPUT.
- Exact replay of an earlier command still returns its history even if the Lot is now REJECTED.
  This is the existing replay contract and is unchanged.
- The existing per-warehouse RELEASED gates stay as they are.
- Callers keep their own error vocabulary: `manufacturing.services` maps `LotRejectedError` to
  `MaterialQualityError`; `demo` screens map it to a Thai message. The Implementer decides the
  class layout; each mapping needs a test.

### PostgreSQL
A deferred constraint trigger on `inventory_stockledgerentry` (AFTER INSERT, checked at commit).
At commit, for each new entry whose Lot is blocked, the entry must be a **debit** and be linked as:
- a `ProductionPosting` of kind SCRAP, or
- the debit entry of a `StockReversal` of a receipt, or
- the entry of a `ProductionPostingReversal` whose posting is an OUTPUT.

Anything else, including an entry with no link, fails the commit. History written before this
migration is never re-checked (insert-time only, as in M6.1).

- **Why deferred:** the ledger entry is inserted before the row that links it, in the same
  transaction. Checking at commit sees both.
- **Why on the ledger entry:** every stock change creates one, so a direct INSERT is covered too.
- **Race:** Quality and Inventory both take the Lot row lock first and hold it to commit, so a
  rejection and a movement of the same Lot serialize. Verified by a two-connection test.
- **Migration:** in `inventory`, depending on `quality` `0007`. Reverse drops the trigger and
  function. It runs `SET CONSTRAINTS ALL IMMEDIATE` before and after, as M6.1 migration 0006 did.

## Acceptance criteria and tests (each written first and seen failing)

**Commands, one test per row**
- REJECTED at the source warehouse, at another warehouse (source RELEASED), and at the destination:
  transfer refused in all three.
- issue, return, CONSUME, receipt, OUTPUT, reversal of a transfer, reversal of a CONSUME, reversal
  of a SCRAP: refused when the Lot is REJECTED at any warehouse.
- SCRAP, reversal of a receipt, reversal of an OUTPUT: succeed when the Lot is REJECTED.
- After REJECTED → HOLD (APPROVER) the same commands work again (gated only by their old rules).
- Exact replay of a transfer made before the rejection returns history.
- Q3: an order holds a Lot on its line, the Lot is rejected at another warehouse: CONSUME and
  return refused, SCRAP works, the order closes after the line is empty.
- Q4: a Lot REJECTED at A is inspected and RELEASED at B: allowed, and still unusable.

**PostgreSQL, by direct SQL** (not through the commands)
- credit or debit with no link, or linked as transfer, receipt, CONSUME, OUTPUT, issue, return or
  reversal of CONSUME/SCRAP/transfer: fails at commit while the Lot is REJECTED.
- debit linked as SCRAP, receipt reversal or OUTPUT reversal: passes.
- the same entries pass when the Lot is not REJECTED anywhere.
- two connections: reject and move the same Lot concurrently; exactly one outcome, never both.

**Migration:** unapply and reapply.

**Screens:** each screen that posts a transfer, issue, return, consume, receipt, output or
reversal shows a message for a blocked Lot (no 500).

**Regression:** full suite, Ruff, `makemigrations --check --dry-run`. Existing tests that insert
bare ledger entries for a REJECTED Lot, if any, are fixed only where they would now fail.

## Documentation (same PR)

- This file: scope, tested SHA, commands and results, review status, closeout after merge.
- `docs/reviews/m62-independent-review.md`: review by a separate session (type stated on its first lines).
- `docs/TASKS.md`: M6.2 stays unchecked in the PR; ticked in the docs PR after the merge.
- `docs/DEVELOPMENT.md`: the rule and a demo walk. `docs/assignments/m61-inspection.md`: mark "refusing
  a REJECTED Lot at other warehouses" as delivered by M6.2 (dated, historical note).
- `README.md`: only if the delivered summary changes.
- Docstrings in `inventory/transfers.py` and `inventory/reversals.py` that describe the gate.

## Process

- Implementer: a sub-agent, test-first, on this branch.
- Reviewer: a separate session, given only the PR number, the Issue number and the path of this
  spec; no Manager commentary. Not started.
- Repair: at most 2 rounds; a third recurrence goes to the owner.
- Verification: local runs are development checks; CI on PostgreSQL 18.6 is the evidence of record.
- The owner merges. After the merge the Manager opens the docs PR and stops (no M6.3).

## Open points for the owner

None blocking. Decisions taken by the Manager, for approval with this spec: the trigger shape
(deferred, on the ledger entry), "anywhere" meaning the Lot's whole organization, and reversal of a
SCRAP being refused because it puts stock back.


## Evidence (Implementer, 2026-11-06)

Review status of this section: it is the Implementer's own record (self-verification), not a review. The independent review is in the next section.

### Scope delivered

- `quality.services.get_rejected_warehouses(lot=)`: read-only; latest event per warehouse (highest id, as
  `get_lot_disposition`), returns the Warehouses where it is REJECTED.
- `inventory/lot_gate.py`: `LotRejectedError` and `require_lot_not_rejected(lot)`. Called after the Lot lock
  and the exact-replay/key-conflict check, before any write, in `_post_transfer` (transfer, issue, return),
  `receive_stock`, `post_production_posting` for CONSUME and OUTPUT (not SCRAP), `reverse_transfer`, and
  `reverse_production_posting` for a CONSUME or SCRAP original (not OUTPUT). Not called by SCRAP,
  `reverse_receipt`, or the reversal of an OUTPUT.
- `manufacturing.services`: `MaterialLotRejectedError(MaterialQualityError)` raised for `LotRejectedError` in
  issue/return, consume/scrap/output and `reverse_order_posting`.
- `demo/views.py` and `demo/production_views.py`: a Thai message ("Lot นี้ถูก REJECTED ที่คลังใดคลังหนึ่ง …",
  with the Lot and warehouses) instead of a 500.
- `inventory/migrations/0015_rejected_lot_guard.py` (depends on `quality` 0007): deferred constraint trigger
  `inventory_ledger_rejected_lot_guard` on `inventory_stockledgerentry`; reversible; `SET CONSTRAINTS ALL
  IMMEDIATE` before and after.
- Docs: `docs/DEVELOPMENT.md` (rule and demo walk), dated note in `docs/assignments/m61-inspection.md`,
  docstrings in `inventory/transfers.py` and `inventory/reversals.py`. `docs/TASKS.md` and `README.md` untouched.

### Rulings made while building (for the Reviewer and the owner to confirm)

1. **Order of the gates.** The new gate runs AFTER the existing per-warehouse RELEASED gate. A Lot REJECTED at
   the source (or at the leaving warehouse of a reversal) is therefore still refused with the old
   `TransferQualityError` / `ReversalQualityError`; only a rejection elsewhere or at the destination gives
   `LotRejectedError`. Reason: the spec says those gates "stay as they are", and two existing tests
   (`test_rejected_lot_cannot_be_transferred`, `test_rejected_destination_blocks_transfer_reversal`) assert them.
   The behaviour is refused in all three transfer positions either way.
2. **`MaterialLotRejectedError`** is a subclass of `MaterialQualityError` (the spec asks for that mapping) so the
   production screen can show a message specific to REJECTED instead of "must be RELEASED at the source".
3. **Test harness.** Django checks deferred constraints at test teardown. A plain `django_db` test runs in one
   transaction, so ledger entries inserted before a Lot is rejected were checked against the later rejection and
   failed teardown (28 errors on the first full run, 9 of them in existing tests). Production commits that history
   earlier. `tests/quality/helpers.settle()` fires the pending checks first; it is called by `force_reject` and by
   the `inspect` helpers of `tests/quality/test_inspection.py` and `tests/web/test_quality_screens.py` when the
   result is FAIL. No assertion in an existing test changed.
4. The trigger reads the latest event per warehouse for the Lot (`DISTINCT ON (warehouse_id) ... ORDER BY
   warehouse_id, id DESC`), the same rule as `get_lot_disposition`. "Anywhere" is the whole Lot, which belongs
   to one organization.

### Tested commit and environment (development check, NOT the evidence of record)

- Tested code commit: `fe8aa71` (the later commits only change documentation). Branch `claude/keen-feynman-jkijlw`,
  base `main` `96d15f9` plus the two spec commits.
- Local: Python 3.14.6 (uv-managed; CI pins 3.14.8), PostgreSQL 16 (CI: 18.6), Django 5.2.18, pytest 9.1.1.
  Throwaway database and role; `.env` not committed.
- CI on PostgreSQL 18.6 is the evidence of record and has not run on this branch yet.

### RED → GREEN log

| Group | RED (before the code) | GREEN |
|---|---|---|
| Quality read function (`tests/quality/test_rejected_warehouses.py`) | 4 failed: `AttributeError: module 'quality.services' has no attribute 'get_rejected_warehouses'` (fixtures and `force_reject` worked) | 4 passed |
| Commands (`tests/inventory/test_rejected_lot_gate.py`) | 15 failed, 5 passed: `DID NOT RAISE LotRejectedError` / `MaterialQualityError` for 14; at the source the old `TransferQualityError` (the test expectation was then changed to ruling 1). The 5 passing are the allowed commands and the replay tests, which already held | 20 passed |
| Screens (`tests/web/test_rejected_lot_screens.py`) | 6 failed: `Internal Server Error` on `/receipts/new/`, `/transfers/new/`, `/reversals/transfer/<pk>/` (unmapped error); production forms showed the generic message without REJECTED | 6 passed (`tests/web` 83 passed) |
| PostgreSQL trigger and migration (`tests/inventory/test_rejected_lot_trigger.py`) | 14 failed: `DID NOT RAISE IntegrityError` for the 11 refused link kinds and the autocommit case, race-with-direct-insert returned `committed`, migration test: trigger absent. 20 passed (allowed kinds, not-rejected, command-level races) | 34 passed |

The refused link kinds covered by direct SQL: credit and debit with no link, receipt, transfer, issue, return, CONSUME,
OUTPUT, reversal of a CONSUME, of a SCRAP and of a transfer. Passing while REJECTED: SCRAP, receipt reversal, OUTPUT
reversal. All 14 kinds pass when the Lot is not REJECTED. Races (two connections, `blocked_action`): movement first
then rejection; rejection first then the waiting command is refused; rejection first then a waiting direct INSERT fails
at its commit.

### Commands and results (development check)

- `uv run --env-file .env pytest -q -p no:cacheprovider` before the change (main `96d15f9` plus spec): 1003 passed in 137.75s.
- Same on `fe8aa71`: **1067 passed in 148.77s** (1003 + 64 new tests). A first run before the `settle()` fix: 1067 passed, 28 errors at teardown.
- `uv run ruff check .`: All checks passed. `uv run ruff format --check .`: clean.
- `uv run --env-file .env python manage.py makemigrations --check --dry-run`: No changes detected.
- `migrate inventory 0014` (unapplies `0015_rejected_lot_guard`: OK) then `migrate` (reapplies: OK), on the
  throwaway database; `tests/inventory/test_rejected_lot_trigger.py::test_migration_unapplies_and_reapplies` does the
  same inside the suite and checks the trigger and function are gone and back.
- The demo walk in `docs/DEVELOPMENT.md` was run against the seeded database with the Django test client
  (transfer, FAIL inspection at RM-B, refused transfer/receipt/issue, return to HOLD, transfer works): all as described.

### Open points for the Reviewer

- Ruling 1 (gate order) and ruling 3 (`settle()` in the test harness).
- The trigger checks only at commit, so a raw INSERT is refused when the transaction ends, not at the statement.

### Independent review (2026-11-06)

[`docs/reviews/m62-independent-review.md`](../reviews/m62-independent-review.md): **independent review by a separate session**,
read-only, code-reading only (no tests run), on `ea2c26f`. Verdict **fix-then-ship**, no code defect: findings 1 (review record
missing) fixed by adding that file; 2 (no CI evidence yet) open until CI finishes at the final SHA; 3 (gate order, ruling 1)
left for the owner to confirm; 4 and 5 not changed. Repair round 1 of 2 touched documentation only and was not re-reviewed.

**Unsupported by design (finding 4):** rejecting a Lot in the same transaction that already inserted a ledger entry for it
fails at commit, because the trigger checks the disposition at commit. No production path does this. M6.3 and M6.4 must not
combine the two in one transaction.

### Closeout

To be written after the owner merges (merge SHA, post-merge CI, TASKS.md tick in the docs PR).
