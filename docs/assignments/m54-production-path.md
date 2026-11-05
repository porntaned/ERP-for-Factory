# M5.4 — test and scrutinize the production path

Repository `porntaned/ERP-for-Factory`; branch `claude/great-bardeen-dumu9p`; base `main` `ea96317`.
[Issue #85](https://github.com/porntaned/ERP-for-Factory/issues/85). Status: **implemented, PR awaiting owner review** ("in progress" held until 2026-11-05 — historical).
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
    - checks that the closed order refuses further issue, output and reversal.
    - (Planned and dropped: "the HOLD output cannot be transferred". `demo-warehouse` has no role
      at FG, so the test would prove authority, not Quality. Transfer Quality is covered since
      M4.3.3.)
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

## Delivered

- `manufacturing/genealogy.py`: `inputs_of` follows only orders where the Lot has nonzero net
  output. The M5.2c test that pinned the old behaviour now expects no inputs.
- `demo/management/commands/seed_production_demo.py`: the scenario above, through the real
  commands, with fixed request UUIDs (`m54-*`). `--reset` flushes first, as in `seed_demo`.
- `tests/manufacturing/test_production_path.py`: 6 tests.
- `docs/DEVELOPMENT.md`: production demo walkthrough.
- `docs/reviews/m5-production-path-review.md`: scrutinize record.
- [Issue #86](https://github.com/porntaned/ERP-for-Factory/issues/86): an order with output can be
  cancelled. This is left for the owner to decide.

## Rulings made while building

1. **The scenario is a separate command; `seed_demo` is unchanged.** The M4.7 walkthrough and
   its tests pin the balance screen to L-0001 = 100 only. Cost if wrong: one extra command.
2. **No new chip receipts into L-0001.** The demo uses new Lots L-0002, L-0003 and D-0001.
3. **Mid-path refusals are not repeated in the path test.** The M5.2a–c unit tests cover them,
   and the spike showed them on PostgreSQL.
4. **Cancel after output becomes an issue, not a fix.** It changes a business rule.

## RED / GREEN

| Task | RED observed | GREEN |
|---|---|---|
| 1 Genealogy | `assert [Link(...)] == []` for LAMP-9; then the M5.2c test pinning the old behaviour failed as intended until updated | 160 passed (manufacturing) |
| 2 Production demo | `CommandError: Unknown command: 'seed_production_demo'` | 6 passed; full suite 925 passed |

## Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6 via `UV_PYTHON=3.14.6` (3.14.8 is not available in this
session). Tested commit `99583d4de8bad28a7ad741a576342b62ef8a3d05`.

| Command | Result |
|---|---|
| `uv run --env-file .env pytest -q` | 925 passed |
| `uv run ruff check .` / `uv run ruff format --check .` | clean |
| `uv run --env-file .env python manage.py makemigrations --check --dry-run` | No changes detected (no schema change) |
| scratch DB: `seed_production_demo --reset`, then the DEVELOPMENT.md shell snippet | `CLOSED One lamp failed end-of-line test`; inputs and outputs as documented |

CI evidence of record: the CI comment on the PR.

## Review

Self-review only (one agent, no sub-agents):
[m5-production-path-review.md](../reviews/m5-production-path-review.md). Verdict fix-then-ship:
two findings fixed, one open as Issue #86, one cosmetic minor.
