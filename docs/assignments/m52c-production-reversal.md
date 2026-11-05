# M5.2c — production reversal, shortfall reason, order messages (design spec)

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `73362a4`.
[Issue #81](https://github.com/porntaned/ERP-for-Factory/issues/81). Status: **design approved,
implementation in progress**. Designed with `superpowers:brainstorming` (architectural path); the
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
