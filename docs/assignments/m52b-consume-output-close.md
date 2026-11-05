# M5.2b — consume, scrap, record output and close a production order

Repository `porntaned/ERP-for-Factory`; branch `claude/dreamy-volta-9v3i8u`; base `main` `2d1f8d5`.
[Issue #75](https://github.com/porntaned/ERP-for-Factory/issues/75). Status: **merged** (PR #76 at `a691b24`, 2026-11-05; "PR awaiting CI" held until then — historical).

## Owner decisions (chat, 2026-11-04)

1. An order closes only when nothing is left on its line; leftovers are returned **or** scrapped.
2. Scrap needs a reason and an APPROVER; the owner approved this stock adjustment (AGENTS.md).
3. Output enters FG as HOLD, waiting for inspection (M6.1).
4. Continuous work with self-merge after green CI, inside the M5–M6 scope.

## Delivered

- `inventory.ProductionPosting` (CONSUME, SCRAP, OUTPUT) owns one ledger entry;
  `inventory/production.py:post_production_posting` posts it. Authority: PRODUCTION for CONSUME
  and OUTPUT, APPROVER for SCRAP, at the posting's warehouse. Locks as receipts (Lot → Item →
  Warehouse → Plant → actor → grant); replay with current authority; key in the shared registry
  under the posting kind.
- PostgreSQL (inventory 0012, reversible): CONSUME/SCRAP entries are debits, OUTPUT entries
  credits; a posting entry belongs to no receipt, transfer or reversal, checked from both sides;
  postings are immutable.
- `manufacturing.OrderPosting` links a posting to its order. Commands `consume_material`,
  `scrap_material`, `record_output(order, lot_code, quantity, …)`, `close_production_order`.
  `ProductionOrder` gains CLOSED with `closed_by`, `closed_at`, `close_request_id`.
- PostgreSQL (manufacturing 0006, reversible): postings only for an OPEN order (row locked);
  consumption/scrap of BOM components on the order line within the order's holding; output of the
  BOM item at the output warehouse, total ≤ order quantity, an output Lot owned by one order with
  no other history; holding must be zero to cancel or close; OPEN → CLOSED allowed, key ORDER_CLOSE.
- Holding of a Lot = issued − returned − consumed − scrapped; returns now respect consumption.

## Rulings

1. Consumption has no Quality gate on the line: the material was RELEASED when issued (M5.2a);
   the line's own pair is HOLD by default and is not used. M6.2 revisits gates.
2. Output total is capped at the order quantity; closing with less (a yield shortfall) is allowed.
3. An output Lot is always new: `record_output` never adopts an existing Lot, so genealogy (M5.3)
   can attribute every unit of it to one order.
4. Production postings are not reversible in M5 (no reversal command); corrections would be a later
   slice. Recorded as deferred.
5. Self-review found that a replay of consume/scrap with a different Lot returned the stored
   record instead of a conflict; fixed — `test_replay_with_another_lot_or_lot_code_conflicts`
   RED → GREEN.

## RED / GREEN

RED: collection error, `ProductionPosting` missing. GREEN: 18 tests in
`tests/manufacturing/test_production_postings.py` (consume limits, returns after consumption,
authority, replay/conflict, scrap with APPROVER and reason, output HOLD, output cap, output Lot
ownership, close rules, closed order, keys, DB sign/exclusivity/immutability, concurrent
consumption).

## Verification (development check, not evidence of record)

PostgreSQL 16.15, Python 3.14.6. Tested commit `5418cdd5c21db9aeca6646789496fb1c501b6a3c`.

| Command | Result |
|---|---|
| `uv run pytest -q` | 888 passed |
| `uv run ruff check .` / `ruff format --check .` | clean |
| `makemigrations --check --dry-run` | No changes detected |
| `migrate manufacturing 0004` → `migrate inventory 0010` → `migrate` | reversible |

CI evidence of record: the CI comment on the PR.

## Review

Self-review only (`scrutinize` trace; one defect fixed as above).

## Closeout (2026-11-05)

PR CI [#206](https://github.com/porntaned/ERP-for-Factory/actions/runs/41939614647) on head `26102c2`: PostgreSQL 18.6, Python 3.14.8, **888 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/76#issuecomment-6645909777)). Merged under the owner's advance authorisation: PR #76 at `a691b243aa33f9d1d1f95170da421ecc8e97a36b`; [main CI #207](https://github.com/porntaned/ERP-for-Factory/actions/runs/41940066477): **888 passed**. Issue #75 closed.
