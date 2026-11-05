# M5.2c — production reversal, shortfall reason, order messages (design spec)

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `73362a4`.
[Issue #81](https://github.com/porntaned/ERP-for-Factory/issues/81). Status: **merged** (PR #83 at `d5711af`, 2026-11-05; "implemented, PR awaiting owner review"
and "design approved, implementation in progress" held until then — historical). Designed with `superpowers:brainstorming` (architectural path); the
owner answered four questions and approved the data/database section in chat on 2026-11-05 and
asked to start work; the command section below was written after that approval and is open to
correction in review. The owner merges; no self-merge.

## Goal

Close three gaps found when the M5 rulings were scrutinized (2026-11-05), before M5.4:

1. CONSUME, SCRAP and OUTPUT postings can be reversed, following M4.5.
2. Closing an order whose output is short needs a reason.
3. Cancel/close refusals name each Lot still on the line and its quantity.

## Owner decisions (chat, 2026-11-05)

From the issue: APPROVER reverses; once only; whole posting; a new opposite entry references the
untouched original; an OUTPUT is reversible only while its Lot has not been used or transferred;
holdings and output totals count reversals.

1. **Order state:** reversal only while the order is OPEN. A CLOSED order is final (reversing
   consumption would put material on a closed line; reversing output would leave an unexplained
   shortfall).
2. **Output Lot "not used":** strict history test. An OUTPUT is reversible only if every ledger
   entry of its Lot is an OUTPUT posting or the reversal of one. Any transfer, consumption,
   scrap, receipt or receipt reversal blocks it, even if the stock came back. The same rule
   replaces "an output Lot has no other history", so after a partial reversal the order may
   output into that Lot again.
3. **Shortfall reason:** required when net output < order quantity, refused when net output ≥
   order quantity ("reason if and only if short").
4. **Storage:** a new table `inventory.ProductionPostingReversal` (not an extension of
   `StockReversal`, not a self-reference on `ProductionPosting`).

Assumptions stated in the brief and not objected to: genealogy nets out reversals; authority is
APPROVER at the posting's warehouse (line for CONSUME/SCRAP, output warehouse for OUTPUT); an
OUTPUT is reversible in any Quality state (as a receipt in M4.5); Quality never changes.

## Data and PostgreSQL rules

**Inventory** (migration 0013 model, 0014 rules, reversible)

- `REQUEST_KEY_COMMANDS` gains `POSTING_REV`.
- `ProductionPostingReversal`: `request_id` (unique), `posting` (one-to-one to
  `ProductionPosting`, PROTECT: once only), `ledger_entry` (one-to-one, PROTECT), `created_at`.
- Insert trigger: the entry has the original's Lot and warehouse and exactly the opposite
  quantity; the entry belongs to no receipt, transfer, stock reversal or production posting;
  for an OUTPUT original, the Lot's other entries are all OUTPUT postings or their reversals.
- Receipts, transfers, stock reversals and production postings cannot adopt a reversal entry.
- Immutable (no update/delete); the registry trigger runs last (`POSTING_REV`).
- Unapplying 0014 is refused while reversals exist (as M4.5 0009).

**Manufacturing** (migration 0007 rules + field, reversible)

- Insert trigger on `inventory_productionpostingreversal`: lock the linked order FOR UPDATE; it
  must be OPEN.
- Holding of a Lot = issued − returned − consumed − scrapped + reversed consumption/scrap.
- Net output = OUTPUT − reversed OUTPUT; used by the output cap and by closing.
- The output-Lot ownership check accepts reversal entries of the same order's outputs.
- `ProductionOrder.shortfall_reason` (text, null): CHECK it is null unless CLOSED and nonblank
  when set; on OPEN → CLOSED a trigger requires it exactly when net output < quantity.

## Commands

**Inventory** — `inventory/production.py`:
`reverse_production_posting(*, posting, actor, reason, request_id) -> ProductionPostingReversal`.
Locks Lot → Item → Warehouse → Plant → actor → APPROVER grant at the posting's warehouse (as
`post_production_posting`). Exact replay (same posting, actor, reason) returns the stored record
with current authority; other reuse is a conflict; a second reversal of one posting raises
`AlreadyReversedError` (reused from `inventory.reversals`). OUTPUT: the history rule above, then a
balance check; violations raise `OutputLotUsedError`. A CONSUME/SCRAP reversal credits the line.

**Manufacturing** — `manufacturing/services.py`:

- `reverse_order_posting(*, order_posting, actor, reason, request_id)` locks the order row,
  refuses unless OPEN, calls Inventory and maps its errors to the `Material*` errors
  (`AlreadyReversedError` passes through; `OutputLotUsedError` → `MaterialLimitError`).
- `close_production_order(*, order, actor, request_id, shortfall_reason=None)`: the reason must
  be nonblank when net output < quantity and absent otherwise; replay also compares it.
- Cancel and close refusals list every nonzero holding, for example
  `return or scrap the material on the line before closing: LED-CHIP lot L1 holds 40`.
  The database messages stay generic.
- `_order_holdings`, `_output_total` and genealogy (`inputs_of`, `outputs_of`) add reversal
  entries; Lots that net to zero drop out of genealogy.

Lock order is unchanged: order row first, then Inventory's order. Reversal and close therefore
serialize on the order row; a reversal of OUTPUT and a transfer of the output Lot serialize on
the Lot row.

## Tests (PostgreSQL)

`tests/manufacturing/test_production_reversal.py`: reversal of each kind (balances, holding,
net output, untouched original); APPROVER at the right warehouse; replay, conflict, other-command
key, once only, `POSTING_REV` registered; CLOSED order refused; output Lot transferred (and back)
refused; RELEASED output still reversible; re-output into a partly reversed Lot; database rules
through raw SQL (exact offset, exclusivity both ways, immutability, used Lot, closed order);
shortfall reason (required, refused, stored, replay, DB check and trigger); refusal messages;
genealogy nets reversals; concurrency (double reversal, reversal vs close, OUTPUT reversal vs
transfer of the output Lot); migration unapply refused with reversals.
Existing M5.2b tests that close a short order pass a `shortfall_reason`.

## Out of scope

Quality gate for consumption (M6.2), screens, Deploy, reopening CLOSED orders.

## Delivered

- Inventory: `ProductionPostingReversal` (migration 0013, `POSTING_REV` key) and rules
  (0014): exact offset, exclusivity both ways, OUTPUT Lot history, immutability, registry last,
  unapply refused while reversals exist. `inventory/production.py:reverse_production_posting`,
  `OutputLotUsedError`; `AlreadyReversedError` reused from M4.5.
- Manufacturing: `reverse_order_posting` (order row locked, OPEN only); migration 0007
  (OPEN-order trigger on reversals, holding and net output include reversals, output Lot may
  hold its own order's output reversals); migration 0008 (`shortfall_reason`, CHECK, close
  trigger); `close_production_order(..., shortfall_reason=None)`; cancel/close refusals list
  each held Lot; genealogy nets reversals.
- Plan: [`m52c-plan.md`](m52c-plan.md) (3 code tasks), executed inline by one agent with
  `superpowers:executing-plans` and `test-driven-development`, as the owner chose.

## Rulings made while building

1. The shortfall rule checks the OPEN → CLOSED transition, not existing rows; an order closed
   short before 0008 keeps no reason. Only synthetic data exists, so nothing is lost.
2. A production posting without an order link cannot be reversed in the database (the OPEN
   check finds no order). Every posting is written with its link, so this is the intended
   behaviour; the Inventory command is called only by Manufacturing.
3. A raw caller of `reverse_production_posting` (outside Manufacturing) locks the Lot before
   the trigger locks the order, the reverse of the command order. This is the same as M5.2b
   postings; only Manufacturing calls it.
4. `test_migrations_unapply_only_without_reversals` was written after migration 0014;
   mutation (refusal removed) made it fail, so it is a real check. The OPEN-order trigger and
   the shortfall trigger were also mutation-checked (each disabled → its database test fails).
5. M5.2b tests that closed a short order now pass `shortfall_reason` (intended contract change).
6. The spec's "unapply refused" applies to inventory 0014; manufacturing 0007/0008 unapply
   freely (they hold no data of their own beyond `shortfall_reason`, which is dropped with the
   column).

## RED / GREEN

| Task | RED observed | GREEN |
|---|---|---|
| 1 Inventory reversal | collection error: `ProductionPostingReversal` missing | 7 passed |
| 2 Manufacturing reversal, totals, genealogy | 11 failed: `ImportError reverse_order_posting` (and raw reversal on a CLOSED order accepted) | 18 passed |
| 3 Shortfall reason, messages | 6 failed (`TypeError` on `shortfall_reason`); then 5 M5.2b close tests failed as intended until updated | 917 passed |
| Self-review fix | `test_order_reversal_rejects_a_malformed_request`: Django `ValidationError` | 26 passed |

## Self-review findings fixed

Review type: **self-review only** (the owner chose one agent, no sub-agents); `scrutinize`
pass on the branch per `docs/SCRUTINIZE.md`.

1. `reverse_order_posting` queried by `request_id` before validating it, so a malformed key
   raised Django's `ValidationError` — fixed (`test_order_reversal_rejects_a_malformed_request`
   RED → GREEN).

Traced without finding a defect: lock order (order row → Lot → Item → Warehouse → Plant →
actor → grant) for reversal, close and transfer; once-only under concurrency; OUTPUT reversal
vs transfer in both orders; close vs CONSUME reversal in both orders; re-output into a
partly reversed Lot through both the Python and database ownership checks; quantity
formatting in messages (`40.000000` → `40`).

Not covered by this slice: screens and admin do not list production reversals (screens are
out of scope).

## Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6 via `UV_PYTHON=3.14.6` (3.14.8 is not available in
this session). Tested commit `a3dbb60268ee85d28b68f812df56dc892abda3bb`.

| Command | Result |
|---|---|
| `uv run --env-file .env pytest -q` | 918 passed |
| `uv run --env-file .env pytest -q tests/manufacturing/test_production_reversal.py` | 26 passed |
| `uv run ruff check .` / `uv run ruff format --check .` | clean |
| `uv run --env-file .env python manage.py makemigrations --check --dry-run` | No changes detected |
| `migrate manufacturing 0006` → `migrate inventory 0012` → `migrate` (dev DB, no reversals) | reversible |

CI evidence of record: the CI comment on the PR.

## Closeout (2026-11-05)

PR CI [#216](https://github.com/porntaned/ERP-for-Factory/actions/runs/41977470766) on head `5133b47` (tested as merge `1c71b75`): PostgreSQL 18.6, Python 3.14.8, **918 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/83#issuecomment-6651002486)). The owner approved the merge in chat; PR #83 merged at `d5711af4012574095e4690d5e7f74681af71b4a1`; [main CI #217](https://github.com/porntaned/ERP-for-Factory/actions/runs/41980499969): **result pending**. Issue #81 closed. Review remained self-review only.
