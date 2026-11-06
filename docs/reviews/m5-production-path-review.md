# M5 production path — scrutinize review (M5.4)

[Issue #85](https://github.com/porntaned/ERP-for-Factory/issues/85). Review type: **self-review**
by the agent that built M5.2c and M5.4, following `docs/SCRUTINIZE.md`. This is not an
independent review. Date: 2026-11-05; base `main` `ea96317`.

## 1. Intent

M5 must let one synthetic product (LAMP-A19) be made through Inventory commands, from issue to a
closed order. Every unit must be accounted for per Lot and warehouse, and the output must be
traceable to its inputs. A smaller solution does not exist without dropping a TASKS.md
requirement. Screens are M7.

## 2. Trace

Entry points traced through `manufacturing/services.py`, `inventory/transfers.py`,
`inventory/production.py`, `manufacturing/genealogy.py` and the triggers in manufacturing
0002–0008 and inventory 0012–0014:

`create_production_order` → `issue_material` (`post_production_transfer`, RELEASED source, net
issue ≤ BOM) → `consume_material` / `scrap_material` (`post_production_posting`, holding ≥
quantity) → `record_output` (new Lot, FG, HOLD, net output ≤ quantity) →
`reverse_order_posting` (OPEN, APPROVER, once, Lot history for OUTPUT) → `return_material` →
`close_production_order` (empty line, shortfall reason iff short) → `inputs_of` / `outputs_of`.

The trace was exercised on PostgreSQL in two ways:
- **Spike:** a throwaway run on a scratch database.
- **Test:** `seed_production_demo` with `tests/manufacturing/test_production_path.py`.

## 3. Verify

| Claim | Path / input | Observed |
|---|---|---|
| Units reconcile per Lot | demo order: L-0002 30 = 28 consumed + 2 scrapped; L-0003 20 = 12 at RM-A + 8 consumed; D-0001 20 = 11 + 9 | `test_every_lot_reconciles_by_warehouse` |
| Output enters FG as HOLD | LAMP-0001/0002 | HOLD at FG |
| Over-issue refused | issue L-0002 1 above 40 chips (spike) | `MaterialLimitError` |
| Refusals name held Lots | close/cancel with L-0002 2, D-0001 1 on the line (spike) | `... LED-CHIP lot L-0002 holds 2, DRIVER lot D-0001 holds 1` |
| Short close needs a reason | close at 9 of 10 without reason (spike) | refused; with reason: CLOSED |
| Closed order is final | issue, output, reversal after close | `MaterialValidationError`, no new rows |
| Rerun posts nothing | `seed_production_demo` twice | counts unchanged |
| Genealogy | LAMP-0001 ← L-0002 28, L-0003 8, D-0001 9; L-0003 → LAMP-0001 5, LAMP-0002 4 | as expected after fix 1 |
| Concurrency | double reversal; close vs reversal; reversal vs transfer (M5.2c tests) | serialized on order / Lot rows |

## 4. Findings

1. **Fixed — a fully reversed output Lot still listed inputs** (`manufacturing/genealogy.py`,
   `inputs_of`).
   - Why it matters: LAMP-0003 (output 1, reversed) claimed it was made from 45 units of
     material.
   - Evidence: the spike printed `inputs_of(LAMP-0003)` = the order's inputs.
   - Change: follow only orders where the Lot has nonzero net output.
   - Test: `test_a_fully_reversed_output_lot_has_no_inputs` RED → GREEN. The owner agreed.
2. **Fixed (demo data) — the demo could not scrap or reverse, and could not issue a full BOM.**
   - Cause: `demo-approver` lacked APPROVER at LINE-1/FG, and there was no DRIVER Lot.
   - Change: `seed_production_demo` grants the role and receives L-0002, L-0003 and D-0001.
   - `seed_demo` is unchanged, so the M4.7 demo keeps L-0001 = 100.
3. **Resolved 2026-11-05 (owner chose option A; see `docs/assignments/m55-production-screens.md`)** — was: open, owner decision, [Issue #86](https://github.com/porntaned/ERP-for-Factory/issues/86):
   an order with output can be CANCELLED.**
   - Cause: `cancel_production_order` and the database check only that the line is empty.
   - Why it matters: the output Lot is left under a cancelled order, and the M5.2c
     shortfall-reason rule is bypassed.
   - Evidence: the spike made order 2 × LAMP-A19 (consume 4, output PROBE-1 1) and cancelled it
     → CANCELLED.
   - Smallest change (option A in the issue): refuse cancel when net output > 0, in the command
     and the trigger. This is a business rule, so it is not fixed here.
4. **Minor (not fixed) — `seed_demo` writes its success line even when called with
   `verbosity=0`** (`seed_production_demo` calls it).
   - Cause: it writes to `self.stdout` unconditionally.
   - Effect: cosmetic.

Earlier rulings re-checked and still standing (M5.2c record):
- A raw caller of `reverse_production_posting` locks the Lot before the order. Only
  Manufacturing calls it.
- Orders closed before manufacturing 0008 have no shortfall reason.

## Verdict

**fix-then-ship** for M5. Findings 1–2 are fixed in this slice. M5 should be ticked once the
owner has ruled on Issue #86 (ruled 2026-11-05: option A; fixed in the PR that records it, awaiting owner merge). The biggest remaining risk is cancel bypassing the close rules.
