# M6.2 — Hold/Release enforced with Inventory

Repository `porntaned/ERP-for-Factory`; branch `claude/keen-feynman-jkijlw`; base `main` `96d15f9`.
[Issue #103](https://github.com/porntaned/ERP-for-Factory/issues/103).
Status: **spec approved by the owner in chat (2026-11-06); implementation started** ("spec, awaiting owner approval; no code written" held until then — historical).

Roles in this slice (stated as they actually happen; updated as work proceeds):
Manager = this Claude Code session. Implementer = sub-agent spawned by the Manager (started 2026-11-06). Reviewer = a separate
session (not started). Owner decides and merges.

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
