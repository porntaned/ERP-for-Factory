# M5.3 — Lot genealogy between inputs and outputs

Repository `porntaned/ERP-for-Factory`; branch `claude/dreamy-volta-9v3i8u`; base `main` `415be0a`.
[Issue #78](https://github.com/porntaned/ERP-for-Factory/issues/78). Status: **merged** (PR #79 at `9675626`, 2026-11-05; "PR awaiting CI" held until then — historical).
Continuous work under the owner's advance authorisation (chat, 2026-11-04).

## Delivered

`manufacturing/genealogy.py`:

- `inputs_of(lot)` → for the order that produced `lot`, each consumed Lot with the quantity
  consumed.
- `outputs_of(lot)` → for every order that consumed `lot`, each output Lot with its output
  quantity and how much of `lot` the order consumed.

Both read immutable M5.2 records: output Lot → order (`OrderPosting` OUTPUT) → consumed Lots
(`OrderPosting` CONSUME). Returned and scrapped material is not part of an output.

## Rulings

1. No genealogy table: the links already exist in immutable, DB-checked records; a second table
   would be a copy to keep consistent. Cost if wrong: one more query per lookup, no data loss.
2. Order granularity: when one order outputs several Lots, each lists all of the order's consumed
   Lots (no apportioning between output Lots). An output Lot belongs to one order (M5.2b), so the
   link is never ambiguous across orders.
3. One level only; multi-level tracing (through WIP) and a screen belong to M6.3.
   Note (2026-11-11): multi-level tracing and the screens were delivered by M6.3 (Issue #108):
   `trace` and `lot_positions` in `manufacturing/genealogy.py`, built on these functions, and the
   `/lots/search/` and `/lots/<pk>/trace/` screens (record: `docs/assignments/m63-lot-trace.md`). `inputs_of` and
   `outputs_of` are unchanged.

## RED / GREEN

RED: `ModuleNotFoundError: manufacturing.genealogy`. GREEN: 4 tests in
`tests/manufacturing/test_genealogy.py` (two input Lots with scrap and return excluded, an input
Lot feeding two orders, Lots without history, unsaved Lot rejected).

## Verification (development check, not evidence of record)

PostgreSQL 16.15, Python 3.14.6. Tested commit `e3a4562e2793ab2c17e0d49f0c69d5a09e8fee9e`:
full suite 892 passed; Ruff clean; no pending migrations (no schema change).

CI evidence of record: the CI comment on the PR.

## Review

Self-review only.

## Closeout (2026-11-05)

PR CI [#210](https://github.com/porntaned/ERP-for-Factory/actions/runs/41941131608) on head `e6f8698`: PostgreSQL 18.6, **892 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/79#issuecomment-6646106029)). Merged under the owner's advance authorisation: PR #79 at `967562686d76fb5adfa69806933956d915c5bae8`; [main CI #211](https://github.com/porntaned/ERP-for-Factory/actions/runs/41941480913): **892 passed**. Issue #78 closed.
