# M6.3 — Trace Lots through every production level

Repository `porntaned/ERP-for-Factory`; branch `claude/keen-feynman-jkijlw`; base `main` `94a3e38`.
[Issue #108](https://github.com/porntaned/ERP-for-Factory/issues/108).
Status: **[PR #111](https://github.com/porntaned/ERP-for-Factory/pull/111) open; independent review by a separate session: fix-then-ship, no code findings, documentation fixes applied; awaiting the owner** (2026-11-11). ("implemented on the branch, not yet reviewed; PR not yet opened", "spec approved by the owner in chat (2026-11-11); implementation started" and "spec, awaiting owner approval; no code written" held until then — historical.)

Roles (as they actually happen; updated as work proceeds): Manager = the main Claude Code session.
Implementer = a sub-agent spawned by the Manager (started 2026-11-11). Reviewer = a separate Claude Code
session (`session_01MVmjhewJFpBspSkUbCyJN4`), given only the PR number, the Issue number and this path; report in [`docs/reviews/m63-independent-review.md`](../reviews/m63-independent-review.md). The owner decides and merges.

## Purpose

M5.3 links an output Lot to the Lots its order consumed, one level only (`manufacturing/genealogy.py`).
The page `/lots/<pk>/genealogy/` shows that one level. When a material Lot is found bad, the factory
needs every finished Lot it went into, through any number of WIP levels, and where that stock is now.
When a finished Lot is found bad, it needs every material Lot behind it. M6.3 adds that trace.

## Current behaviour (traced in code, `main` `c0f600d`)

- `inputs_of(lot)`: Lots consumed by the order that output `lot`, with net consumed quantity.
- `outputs_of(lot)`: output Lots of every order that consumed `lot`, with net output and how much of
  `lot` the order consumed.
- Both read immutable `OrderPosting` rows. Reversed postings net out; a net of zero is not listed.
  Links are per order, not apportioned between output Lots of one order (M5.3 ruling 2).
- Multi-level chains are possible today: a BOM item may be `WIP` or `FINISHED`, and a component may
  be `RAW` or `WIP` (`manufacturing/services.py:131`, `:144`). The demo has no WIP item.
- Nothing prevents a Lot cycle in all cases (an open order could consume a Lot made downstream of
  its own output). The trace must not loop.
- `/lots/<pk>/genealogy/` needs login only (`demo/production_views.py:80`). There is no Lot search.

## Owner rulings (chat, 2026-11-11)

1. **Depth:** the whole chain in both directions: backward to Lots that no order produced (received
   material), forward to Lots that no order consumed. No depth cap. A Lot is expanded once.
2. **Access:** any logged-in user, as the genealogy page today. No role change.
3. **Content per Lot:** the links (order, Lot, item, quantity consumed or output) plus, for each Lot,
   its current balance and Quality disposition per warehouse. Read-only: no HOLD or other action.
4. **Demo:** `seed_production_demo` gains one WIP level so the demo shows a RAW → WIP → FINISHED
   chain. Synthetic data only; no new role or grant.

## Scope

In:
- a trace read model in `manufacturing` built on the M5.3 links;
- screens: a Lot search and a trace page, linked from the genealogy page;
- demo data for one WIP level;
- tests (RED first) and documentation.

Out: M6.4, M7, a HOLD/recall action from the trace, apportioning between output Lots of one order,
supplier or receipt detail beyond what the balance shows, CSV export, the m4 performance of
`/quality/`, any schema change, refactors not needed here (noted in the report instead).

## Design

### Read model (`manufacturing/genealogy.py`)
- `trace(lot, direction)` with `direction` `"backward"` (inputs) or `"forward"` (outputs). It returns
  the start Lot and a list of edges `(level, from_lot, order, to_lot, quantity)`, breadth-first, in a
  stable order (level, order id, Lot code). It reuses the M5.3 netting, so reversed postings and
  zero nets are excluded in exactly the same way.
- A Lot already expanded is not expanded again: the edge is still listed, marked as a repeat, so a
  cycle or a diamond shows once and the walk ends.
- Queries grow with the number of levels, not the number of Lots (one batch per level).
- `lot_positions(lots)`: for each Lot, every warehouse with a nonzero balance, with the balance and
  the disposition there (`get_lot_disposition` rule, read in batch), plus every warehouse where the
  Lot is REJECTED even at zero balance. Read-only; reads Inventory and Quality data, writes nothing.

### Screens (`demo`)
- `/lots/search/?code=…`: login required. Exact Lot code, any item; 0 results shows a message, 1
  redirects to its trace, several list them by item.
- `/lots/<pk>/trace/`: login required. Two sections, "ย้อนไปวัตถุดิบ" (backward) and "ไปยังผลผลิต"
  (forward), each listing edges by level with order and Lot links; a positions table for every Lot
  in the trace (balance and disposition per warehouse; REJECTED stands out).
- The genealogy page links to the trace; the nav or production list links to the search.

### Demo data (`seed_production_demo`)
- New WIP item `LED-BOARD` (BOM: 4 LED-CHIP) and new FINISHED item `LAMP-BR30` (BOM: 1 LED-BOARD
  + 1 DRIVER), drafted by `demo-production` and approved by `demo-approver` through the real commands.
- New Lots only, received and inspected through the real commands, so every balance the existing
  M4.7 and M5.4 walkthroughs describe stays the same.
- Order A outputs a LED-BOARD Lot to FG; `demo-quality` passes its FINAL inspection at FG; order B
  issues it from FG to LINE-1 and outputs a LAMP-BR30 Lot. Existing grants cover every step
  (`demo-production` PRODUCTION at RM-A, LINE-1, FG; `demo-quality` QUALITY at FG).
- Fixed request keys, so a rerun posts nothing new; `--reset` gives the same end state.

## Acceptance criteria and tests (each written first and seen failing)

Read model:
- backward and forward through RAW → WIP → FINISHED: every Lot and level, with net quantities;
- reversed postings and zero nets excluded (same results as `inputs_of`/`outputs_of` at level 1);
- one material Lot feeding two orders, and one order with two output Lots (order granularity);
- a diamond and a cycle built in a test: each Lot expanded once, the walk ends;
- a Lot with no production history: empty trace;
- unsaved Lot refused;
- query count bounded by levels (`django_assert_max_num_queries` with a chain of known depth);
- `lot_positions`: balances per warehouse; HOLD, RELEASED, REJECTED; REJECTED shown at zero balance.

Screens:
- login required on both pages;
- search: 0, 1 (redirect) and several results; Unicode code; blank code;
- trace page shows both directions, the positions table and links to orders and Lots;
- genealogy page links to the trace.

Demo:
- `seed_production_demo --reset` builds the chain; the trace of the LAMP-BR30 Lot reaches its chip
  and driver Lots; the existing M4.7 and M5.4 balances are unchanged; a rerun adds nothing.

Regression: full suite, Ruff check and format, `makemigrations --check --dry-run` (expected: no
changes).

## Documentation (same PR)

- This file: scope delivered, development-check commands and results with the commit they ran on,
  review status, and the link to the PR's CI comment (AGENTS.md, as amended by PR #106).
- `docs/reviews/m63-independent-review.md`: review by a separate session.
- `docs/DEVELOPMENT.md`: the trace walkthrough on the demo data.
- `docs/assignments/m53-lot-genealogy.md`: dated note that multi-level tracing and the screen were
  delivered by M6.3.
- `docs/TASKS.md`: M6.3 stays unchecked in the PR; ticked in the post-merge docs PR.
- `README.md`: only if the delivered summary changes (in the post-merge docs PR).

## Process

- Implementer: a sub-agent, test-first, on this branch.
- Reviewer: a separate session, given only the PR number, the Issue number and this path.
- Repair: at most 2 rounds; a third goes to the owner.
- Local runs are development checks; CI on PostgreSQL 18.6 is the evidence of record, cited by link
  while the PR is open.
- The owner merges (or tells the Manager to). The post-merge docs PR follows at once.

## Decisions taken by the Manager (for approval with this spec)

1. The trace lives in `manufacturing/genealogy.py`, next to the one-level functions it builds on.
2. A repeated Lot is listed but not expanded again (cycle and diamond safety).
3. Search is by exact Lot code; several matches are listed by item.
4. Demo names `LED-BOARD` and `LAMP-BR30`, the chain through FG with a FINAL inspection there.

## Evidence (implementer sub-agent, 2026-11-11)

Review so far: **none** (no self-review or independent review is claimed here; the independent
review by a separate session is still to come). CI on PostgreSQL 18.6 is the evidence of record and
is cited by link to the PR's CI comment once the PR exists; nothing below replaces it.

### Scope delivered

- `manufacturing/genealogy.py`: `trace(lot, direction)` returning `Trace(lot, direction, edges)`
  with `Edge(level, from_lot, order, to_lot, quantity, consumed, repeat)` and a `lots` property;
  `lot_positions(lots)` returning `{Lot id: [Position(warehouse, balance, disposition)]}`.
  `inputs_of` / `outputs_of` unchanged.
- `demo`: `/lots/search/` (`lot_search`, `LotSearchForm`, `lot_search.html`) and
  `/lots/<pk>/trace/` (`lot_trace`, `trace.html`); a **ค้นหา Lot** menu link; the genealogy page
  links to the trace. Login only; no POST form.
- `seed_production_demo`: LED-BOARD / LAMP-BR30 items and BOMs, Lots L-0004, D-0002,
  LED-BOARD-0001, LAMP-BR30-0001, orders #2 and #3 (both CLOSED), one FINAL inspection at FG.
- No schema change, no migration, no new role or grant, no new dependency.

### Rulings made while building (for the reviewer and the owner)

1. Edge order inside a level: order id, then the reached Lot's code, then the expanded Lot's code
   (ids break ties). The first edge to reach a Lot expands it; later ones are `repeat`.
2. Forward edges also carry `consumed` (how much of the expanded Lot the order consumed), so level 1
   equals `outputs_of` field for field; backward edges leave it `None`.
3. `trace` reloads the start Lot with its item (one query) so the screen needs no extra query per
   edge; the bound is 1 + 4 per expanded level + 1 for the last frontier.
4. `lot_positions` reads the latest `LotDispositionEvent` per pair in one `DISTINCT ON` query, the
   same rule as `quality.services.get_lot_disposition` (and as `get_rejected_warehouses`); a test
   checks every position against `get_stock_balance` and `get_lot_disposition`. It lives in
   `manufacturing/genealogy.py` as the spec says, rather than as a new Quality batch function.
5. Search strips surrounding spaces only; the match is otherwise exact (case-sensitive). A blank
   code shows the form only. Django's `CharField` refuses a NUL character, which is shown as
   "รหัส Lot ไม่ถูกต้อง" instead of reaching PostgreSQL.
6. The positions table lists every Lot of both directions once (start Lot first); a Lot with no
   position shows "ไม่มียอดคงเหลือ". REJECTED rows carry `table-danger` and bold text.
7. Demo: the chain's two orders are closed with full output (no shortfall), so the demo leaves no
   open order behind; chip and driver Lots are received with more than the orders use (L-0004 30,
   D-0002 10) so the trace shows remaining stock. Lot codes are the item code plus a serial
   (`LED-BOARD-0001`, `LAMP-BR30-0001`), so the M6.1 Quality list still starts with LAMP-0001.
8. The cycle test is built through the real commands: a second WIP item `BOARD2` is created as
   test master data (`Item.objects.create`, as the fixtures do), then BOMs, orders, issues,
   consumptions, outputs and FINAL inspections all go through the commands. The diamond is built
   the same way.

Existing tests changed because the seed now has three orders, three BOMs and one more FG
inspection (no assertion removed): `tests/manufacturing/test_production_path.py` (`seeded` selects
the LAMP-A19 order; the exact stock table gains the seven M6.3 rows, the ten earlier rows are
unchanged); `tests/web/test_production_screens.py` (`plant` selects the LAMP-A19 order; the exact
order list gains the two new rows; `open_order` selects the ACTIVE LAMP-A19 BOM and the one order
not seeded); `tests/web/test_quality_screens.py` (three inspection counts at FG compare with a
count taken at the start of the test instead of 0).

### RED / GREEN (development checks, PostgreSQL 16.15, Python 3.14.6, Django 5.2.18)

| Group | RED | GREEN | Commit |
|---|---|---|---|
| `trace` | `ImportError: cannot import name 'trace'`; with a stub raising `NotImplementedError`, 9 failed (fixtures built through the commands; first run also showed the chain fixture's order B needed quantity 6, `MaterialLimitError: output would exceed the order quantity`) | `tests/manufacturing/test_trace.py` 9 passed | `9a3b0e0` |
| `lot_positions` | stub: 2 failed, `NotImplementedError` | 11 passed | `6b1afa5` |
| screens | 10 failed (404 for the new URLs, no menu or genealogy link); `test_unknown_lot_trace_is_404` passed before the route existed | `tests/web/test_trace_screens.py` 11 passed | `bde05d2` |
| demo seed | 7 failed (no LED-BOARD/LAMP-BR30 BOMs, orders, Lots or stock rows; the two updated exact tables); the rerun and `--reset` tests passed before the change (they compare states) | after the seed change, 11 errors and 3 failures in existing tests that assumed one order, BOM or FG inspection, fixed as listed above; then `tests/manufacturing/` + `tests/web/` 281 passed | `c73c15d` |

### Development-check commands and results

Run on commit `c73c15d` (clean tree), PostgreSQL 16.15 local cluster, Python 3.14.6:

- `UV_PYTHON=3.14 uv run --env-file .env pytest -q` → **1096 passed** (baseline on `0b0d471`:
  1067 passed; 29 new tests).
- `uv run ruff check .` → All checks passed; `uv run ruff format --check .` → 264 files already
  formatted.
- `uv run --env-file .env python manage.py makemigrations --check --dry-run` → No changes detected.
- On a throwaway database: `migrate`, `seed_production_demo --reset` twice, then a plain rerun:
  orders `(1 LAMP-A19 CLOSED), (2 LED-BOARD CLOSED), (3 LAMP-BR30 CLOSED)`, 37 ledger entries.
  Through the Django test client as `demo-warehouse`: `/lots/search/?code=LAMP-BR30-0001` → 302 to
  its trace; backward rows `1 LAMP-BR30-0001 #3 D-0002 5`, `1 LAMP-BR30-0001 #3 LED-BOARD-0001 5`,
  `2 LED-BOARD-0001 #2 L-0004 20`; forward empty; positions LAMP-BR30-0001 FG 5 HOLD, D-0002 RM-A 5
  RELEASED, LED-BOARD-0001 none, L-0004 RM-A 10 RELEASED. The L-0004 trace reaches
  LAMP-BR30-0001. The shell snippets in `docs/DEVELOPMENT.md` were run on the same data.

CI evidence of record: [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/111#issuecomment-6786212132) (always shows the latest head). ("linked here once the PR exists" held until PR #111 was opened — historical.)

Documentation commits after `c73c15d` are documentation only.
