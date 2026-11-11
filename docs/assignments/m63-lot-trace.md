# M6.3 — Trace Lots through every production level

Repository `porntaned/ERP-for-Factory`; branch `claude/keen-feynman-jkijlw`; base `main` `94a3e38`.
[Issue #108](https://github.com/porntaned/ERP-for-Factory/issues/108).
Status: **spec approved by the owner in chat (2026-11-11); implementation started** ("spec, awaiting owner approval; no code written" held until then — historical).

Roles (as they actually happen; updated as work proceeds): Manager = the main Claude Code session.
Implementer = a sub-agent spawned by the Manager (started 2026-11-11). Reviewer = a separate Claude Code
session (not started). The owner decides and merges.

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
