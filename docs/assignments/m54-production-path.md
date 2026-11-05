# M5.4 — test and scrutinize the production path

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `ea96317`.
[Issue #85](https://github.com/porntaned/ERP-for-Factory/issues/85). Status: **in progress**.
Designed with `superpowers:brainstorming`. A throwaway spike ran one LAMP-A19 order through the
real commands on a scratch database. After seeing its results, the owner chose option A and
agreed that a fully reversed output Lot should list no inputs (chat, 2026-11-05).

## Goal

Prove that one synthetic product can be made end to end on PostgreSQL. Leave the path as
rerunnable demo data, and review the whole M5 path as an outsider before M5 closes.

## Spike findings (2026-11-05, throwaway, scratch database `erp_spike`)

1. `seed_demo` gives `demo-approver` APPROVER only at RM-A/RM-B, so scrap and reversal are
   impossible in the demo.
2. `inputs_of(LAMP-0003)` listed the order's inputs although its only output was reversed (net 0).
3. The demo has one chip Lot and no DRIVER Lot, so an order cannot be issued in full.

All else matched: over-issue refused; held Lots named in refusals; shortfall reason required;
balances reconcile per Lot (e.g. 100 = 70 + 28 consumed + 2 scrapped).

## Design

- **`seed_production_demo`** (new command, `demo/management/commands/`):
  - Runs `seed_demo` first, then the scenario below through the real commands, with fixed demo
    request UUIDs, so a rerun replays and posts nothing new.
  - `seed_demo` itself is unchanged, so the M4.7 walkthrough (L-0001 100 → 70/30) still holds.
  - Grants `demo-approver` APPROVER at LINE-1 and FG.
  - Receives chip Lots L-0002 30 and L-0003 20, and DRIVER Lot D-0001 20, at RM-A, all RELEASED.
- **Scenario:** order 10 × LAMP-A19.
  1. Issue L-0002 30, L-0003 10 and D-0001 10.
  2. Consume L-0002 28, L-0003 8 and D-0001 9. A mistaken second consumption of L-0003 2 is
     reversed.
  3. Scrap L-0002 2 (APPROVER).
  4. Output LAMP-0001 5 and LAMP-0002 4. LAMP-0003 1 is recorded and then reversed.
  5. Return L-0003 2 and D-0001 1.
  6. Close with shortfall reason "One lamp failed end-of-line test".
- **Genealogy fix:** `inputs_of(lot)` only follows orders where `lot` has nonzero net output.
- **Tests (PostgreSQL):**
  - `tests/manufacturing/test_genealogy.py`: a fully reversed output Lot has no inputs.
  - `tests/manufacturing/test_production_path.py`:
    - seeds twice and checks rerun idempotence (ledger and record counts unchanged);
    - checks the closed order, its reason, every Lot × warehouse balance and Quality state, and
      genealogy in both directions;
    - checks that the closed order refuses further issue, output and reversal;
    - checks that the HOLD output cannot be transferred.
  - Mid-path refusals (over-issue, held-Lot messages, missing reason) are already covered by the
    M5.2a–c unit tests and are not repeated.
- **Docs:**
  - `DEVELOPMENT.md` walkthrough (command and a shell snippet printing balances and genealogy).
  - Scrutinize record `docs/reviews/m5-production-path-review.md` (self-review).
  - This record and TASKS.md.

## Plan (inline, TDD; owner: one agent, self-review)

1. Genealogy fix: RED test → change `manufacturing/genealogy.py` → GREEN → commit.
2. `seed_production_demo` + `test_production_path.py`: RED (command missing) → command → GREEN →
   full suite → commit.
3. Scrutinize the M5 path (trace issue → consume/scrap → output → reversal → close → genealogy,
   including locks and database rules). Small defects: TDD fix in this slice. Larger: new issue.
4. Docs, PR.

## Out of scope

Manufacturing screens (M7), the Quality gate for consumption (M6.2), Deploy.
