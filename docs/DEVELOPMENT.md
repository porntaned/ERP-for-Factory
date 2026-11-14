# Development and test environment

## Version contract

The first issue uses exact versions so local and CI evidence can be reproduced:

- Python 3.14.8
- Django 5.2.18 LTS
- PostgreSQL 18.6
- psycopg 3.3.6 with the binary extra
- pytest 9.1.1
- pytest-django 4.14.0
- Ruff 0.17.1
- uv 0.13.1 in CI

The version choices follow the supported Django 5.2 LTS line, the current Python 3.14
maintenance release and the current PostgreSQL 18 minor release as of 2026-10-19. Update an
exact pin only in a separate reviewed change with the relevant checks rerun.

Primary version references:

- [Python 3.14.8 release](https://www.python.org/downloads/release/python-3148/)
- [Django supported versions](https://www.djangoproject.com/download/)
- [Django 5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [Psycopg installation support](https://www.psycopg.org/psycopg3/docs/basic/install.html)
- [uv 0.13.1 release](https://github.com/astral-sh/uv/releases/tag/0.13.1)

## Configuration boundary

`config.settings` requires the secret key and every PostgreSQL connection value from environment
variables. Copy `.env.example` to `.env`, replace every placeholder and keep `.env` outside Git.
The repository contains no development or CI credentials. GitHub Actions uses synthetic job-only
values and a disposable PostgreSQL service.

Required variables:

- `DJANGO_SECRET_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

`DJANGO_DEBUG` is optional and defaults to `false`.

## Local commands

Setting up from nothing (PostgreSQL role and database, `.env`, dependencies, `check`, `migrate`,
`pytest`, the demo seeds and `runserver`) is in the [Install guide](INSTALL.md), in bash; the CI
job `install-guide` runs the same commands, and the match is checked automatically by
[`scripts/check_install_guide.py`](../scripts/check_install_guide.py) in that job. Until
2026-11-12 this section listed part of that setup in PowerShell (`Copy-Item .env.example .env`,
`uv sync`, `check`, `pytest`) without `migrate`, the seeds or the role and database — historical,
replaced by the guide on 2026-11-12. The guide is not tested on Windows.

Developer-only commands the guide does not cover (CI runs both checks):

```bash
uv run ruff check .
uv run ruff format --check .
uv run ruff format .
```

SQLite is deliberately unsupported because it cannot prove the PostgreSQL constraints or
concurrency behavior required by Issue #1.

## Inventory demo walkthrough (M4.7)

Use a disposable database: `seed_demo --reset` flushes every table.

```bash
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py seed_demo --reset   # receives 100 of L-0001 at RM-A, RELEASED
uv run --env-file .env python manage.py set_demo_passwords  # prompts for a password (min 8 chars)
DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver
```

1. Open `http://127.0.0.1:8000/accounts/login/` and log in as `demo-warehouse`.
2. The balance page shows `L-0001 · RM-A · 100 · RELEASED`.
3. **โอน**: lot `L-0001`, source `RM-A`, destination `RM-B`, quantity `30`, any reason → **บันทึกการโอน**.
4. The balance page shows `RM-A 70 RELEASED` and `RM-B 30 HOLD` (the destination keeps its own
   Quality state, M4.3.3).
5. **ประวัติ** lists receipt `R1` (+100) and transfer `T1` (RM-A → RM-B, 30). Reverse buttons
   appear only for `demo-approver`.

`tests/web/test_m47_demo.py` runs the same steps through HTTP on PostgreSQL. Screenshots:
`docs/evidence/m47/`.

## Production demo walkthrough (M5.4)

`seed_production_demo` runs `seed_demo` first, then makes one LAMP-A19 order end to end through
the real commands. Since M6.3 it also makes a RAW → WIP → FINISHED chain with new Lots (see
"Lot trace (M6.3)" below); everything described in this section is unchanged by it. The result can be read in the shell below or on the M5.5 screens ("no screens yet (M7)" was true until M5.5 — historical, corrected 2026-11-06).
Use a disposable database: `--reset` flushes every table.

```bash
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py seed_production_demo --reset
```

```bash
uv run --env-file .env python manage.py shell -c "
from inventory.models import Lot
from manufacturing.genealogy import inputs_of, outputs_of
from manufacturing.models import ProductionOrder
o = ProductionOrder.objects.get(bom__item__code='LAMP-A19')
print(o.status, o.shortfall_reason)
print([(i.lot.code, str(i.quantity)) for i in inputs_of(Lot.objects.get(code='LAMP-0001'))])
print([(i.lot.code, str(i.quantity)) for i in outputs_of(Lot.objects.get(code='L-0003'))])
"
```

What it records (order 10 × LAMP-A19 = 4 LED-CHIP + 1 DRIVER each):

1. New Lots received and RELEASED at RM-A: chips L-0002 30 and L-0003 20; DRIVER D-0001 20.
2. Issue to LINE-1: L-0002 30, L-0003 10, D-0001 10.
3. Consume L-0002 28, L-0003 8 and D-0001 9.
4. A second consumption of L-0003 2 is keyed by mistake; `demo-approver` reverses it.
5. `demo-approver` scraps L-0002 2.
6. Output LAMP-0001 5 and LAMP-0002 4 into FG as HOLD. LAMP-0003 1 is recorded and then
   reversed.
7. Return L-0003 2 and D-0001 1 to RM-A.
8. Close with net output 9 of 10 and the shortfall reason "One lamp failed end-of-line test".

Expected shell output:
- `CLOSED One lamp failed end-of-line test`
- LAMP-0001's inputs: L-0002 28, L-0003 8, D-0001 9.
- L-0003's outputs: LAMP-0001 5 and LAMP-0002 4.

L-0001 is untouched, so the M4.7 walkthrough above still starts from 100 at RM-A.
The shell above selects the LAMP-A19 order: since M6.3 the seed makes three orders, and
`ProductionOrder.objects.get()` (true until M6.3 — historical, corrected 2026-11-11) now fails.

Since M6.1 (Issue #96) both seeds release RM-A Lots with a passing INCOMING inspection. A database
seeded before M6.1 must be reseeded with `--reset`: its old release key belongs to an event without
an inspection, so the rerun reports a key conflict.
`tests/manufacturing/test_production_path.py` checks the same results on PostgreSQL.

**On the web (M5.5):**
1. Run `set_demo_passwords`, then `runserver`, as in the M4.7 walkthrough.
2. Log in as any demo user and open **การผลิต** (`/production/`).
3. Order #1 shows each material Lot (issued, returned, consumed, scrapped, on the line), the
   outputs with their Quality and reversal, the history and the shortfall reason.
4. Click a Lot to open its genealogy (`/lots/<id>/genealogy/`).

5. To record production yourself (M5.5 PR 2), log in as `demo-production`.
   - **การผลิต → สร้าง order**, for example 2 × LAMP-A19 on LINE-1 → FG.
   - Then use the buttons in order: **เบิก** (L-0001 and D-0001 from RM-A), **ใช้**,
     **บันทึกผลผลิต** (a new Lot code), **ปิด order**.
   - As `demo-approver` you can also use **Scrap**, and **กลับรายการ** on a history row.
   - Short output needs a reason when closing.
   - **ยกเลิก order** (Issue #86): refused while the order has net output; reverse the output
     first (as `demo-approver`) and return or use the material on the line, then cancel.
   - A refused action shows why and records nothing.

## Lot trace (M6.3, Issue #108)

`manufacturing.genealogy.trace(lot, "backward" | "forward")` follows the M5.3 links through every
production level: backward to Lots no order produced (received material), forward to Lots no order
consumed. Quantities are net of reversals, as `inputs_of` / `outputs_of`. A Lot reached a second
time (a diamond or a cycle) is listed once more as a repeat and not expanded again. Links are per
order, not apportioned between the output Lots of one order. `lot_positions(lots)` gives each Lot's
balance and Quality disposition per warehouse, plus any warehouse where it is REJECTED at zero
balance. Both only read; there is no HOLD or recall action.

Demo data: `seed_production_demo` adds, with new Lots only and the existing grants:
1. BOMs LED-BOARD v1 (WIP: 4 LED-CHIP) and LAMP-BR30 v1 (FINISHED: 1 LED-BOARD + 1 DRIVER),
   drafted by `demo-production` and approved by `demo-approver`.
2. Chip Lot L-0004 30 and DRIVER Lot D-0002 10 received and RELEASED at RM-A.
3. Order #2, 5 × LED-BOARD: issue and consume 20 of L-0004, output LED-BOARD-0001 5 into FG,
   close. `demo-quality` passes its FINAL inspection at FG (RELEASED).
4. Order #3, 5 × LAMP-BR30: issue LED-BOARD-0001 5 from FG and D-0002 5 from RM-A, consume both,
   output LAMP-BR30-0001 5 into FG (HOLD), close.

New balances: L-0004 RM-A 10 RELEASED; D-0002 RM-A 5 RELEASED; LED-BOARD-0001 0 at FG and LINE-1;
LAMP-BR30-0001 FG 5 HOLD. The M4.7 and M5.4 balances above do not change.
(Order numbers #2 and #3 hold after `--reset`, which restarts the id sequences.)

**On the web:** after `seed_production_demo --reset`, `set_demo_passwords` and `runserver`, log in as
any demo user.
1. **ค้นหา Lot** (`/lots/search/`): enter `LAMP-BR30-0001`. One match opens its trace
   (`/lots/<id>/trace/`); several Lots with the same code (different items) are listed by item;
   none shows "ไม่พบ Lot". The code must match exactly.
2. **ย้อนไปวัตถุดิบ** lists level 1: order #3 used D-0002 5 and LED-BOARD-0001 5; level 2: order #2
   used L-0004 20. **ไปยังผลผลิต** is empty (nothing consumed the lamp).
3. The positions table shows LAMP-BR30-0001 FG 5 HOLD, D-0002 RM-A 5 RELEASED, LED-BOARD-0001 with
   no balance and L-0004 RM-A 10 RELEASED. A REJECTED row is highlighted.
4. Click L-0004: **ไปยังผลผลิต** shows LED-BOARD-0001 (level 1) and LAMP-BR30-0001 (level 2).
5. A Lot's genealogy page (`/lots/<id>/genealogy/`) links to its trace.

Shell:

```bash
uv run --env-file .env python manage.py shell -c "
from inventory.models import Lot
from manufacturing.genealogy import lot_positions, trace
t = trace(Lot.objects.get(code='LAMP-BR30-0001'), 'backward')
print([(e.level, e.from_lot.code, e.order.pk, e.to_lot.code, str(e.quantity)) for e in t.edges])
p = lot_positions(t.lots)
print({l.code: [(x.warehouse.code, str(x.balance), x.disposition) for x in p[l.pk]] for l in t.lots})
"
```

`tests/manufacturing/test_trace.py`, `tests/manufacturing/test_wip_demo.py` and
`tests/web/test_trace_screens.py` cover the same behaviour on PostgreSQL.

## Quality inspection (M6.1, shell)

Only an inspection moves a Lot-Warehouse out of HOLD: PASS → RELEASED, FAIL → REJECTED. The kind
(INCOMING or FINAL) follows the Lot's origin. The sample may not exceed the balance there, and the
note is required. A REJECTED pair returns to HOLD only through an APPROVER who is not the rejecting
inspector.

**On the web (M6.1 PR 2):** after `seed_production_demo --reset`, `set_demo_passwords` and
`runserver`:
1. Log in as `demo-quality` and open **คุณภาพ** (`/quality/`). LAMP-0001 (5) and LAMP-0002 (4) are
   HOLD at FG. Since M6.3, LAMP-BR30-0001 (5) is also HOLD at FG (added 2026-11-11).
2. Record **PASS** (sample 1, any note) on LAMP-0001: it becomes RELEASED and leaves the list.
3. Record **FAIL** on LAMP-0002: it becomes REJECTED.
4. Log in as `demo-approver` (APPROVER at FG from `seed_production_demo`): the REJECTED row has **ส่งกลับ HOLD**; with a reason
   it returns to HOLD and can be inspected again.
5. A Lot's genealogy page (`/lots/<id>/genealogy/`) lists its inspections and disposition history.
`seed_demo` grants `demo-quality` QUALITY at FG and `seed_production_demo` grants `demo-approver`
APPROVER at FG for this (owner-approved, 2026-11-06). The inspector who rejected a pair never sees
its return button. The shell still works ("web screens come in M6.1 PR 2" held until then — historical):

```bash
uv run --env-file .env python manage.py shell -c "
from decimal import Decimal; from uuid import uuid4
from django.contrib.auth import get_user_model
from facilities.models import Warehouse; from inventory.models import Lot
from quality.services import get_lot_disposition, record_inspection, return_rejected_to_hold
U = get_user_model().objects; wh = Warehouse.objects.get(code='RM-A')
lot = Lot.objects.get(code='L-0001')  # RELEASED by the seed; use a HOLD Lot to inspect
print(get_lot_disposition(lot=lot, warehouse=wh))
"
```

`record_inspection(lot=…, warehouse=…, result='PASS'|'FAIL', sample_quantity=Decimal('1'),
note='…', actor=<QUALITY user at that warehouse>, request_id=uuid4())` and
`return_rejected_to_hold(lot=…, warehouse=…, actor=<APPROVER there>, reason='…', request_id=uuid4())`.
In the demo data, `demo-quality` has QUALITY at RM-A, RM-B and FG ("only at RM-A" — historical, corrected 2026-11-06).

## A REJECTED Lot is unusable everywhere (M6.2, Issue #103)

Owner ruling (2026-11-06): while a Lot is REJECTED at **any** warehouse of its organization, it may
not be used at any warehouse, but it may still be scrapped.

- **Refused** (Inventory raises `inventory.lot_gate.LotRejectedError`): transfer (either side), issue,
  return, CONSUME, a further receipt, a further OUTPUT, and the reversal of a transfer, a CONSUME or a
  SCRAP.
- **Still allowed** (they only take stock out): SCRAP, the reversal of a receipt, the reversal of an
  OUTPUT.
- Exact replay of a command made before the rejection still returns its history.
- A Lot issued to a line stays HOLD there and is not inspected again. If it is REJECTED elsewhere, the
  order is frozen for that Lot: only SCRAP by an APPROVER clears the line, then the order closes.
  Nothing is adjusted automatically.
- Inspecting the Lot at another warehouse (REJECTED at A, PASS at B) is recorded, but the Lot stays
  unusable until it is no longer REJECTED anywhere (REJECTED → HOLD by an APPROVER).
- The commands check this after the Lot lock and the exact-replay check, before any write
  (`quality.services.get_rejected_warehouses` is the Quality read). PostgreSQL re-checks at commit
  (migration `inventory/0015_rejected_lot_guard.py`): a new ledger entry of a REJECTED Lot must be a
  debit linked as a SCRAP, a receipt reversal or an OUTPUT reversal. History written earlier is not
  re-checked. The existing per-warehouse RELEASED gates are unchanged and still run first.

Demo walk (disposable database; after `seed_production_demo --reset`, `set_demo_passwords`, `runserver`):
1. As `demo-warehouse`, **โอน** L-0001 from RM-A to RM-B, quantity 20. RM-B holds 20 as HOLD.
2. As `demo-quality`, open **คุณภาพ**, record **FAIL** on L-0001 at RM-B (sample 1). It is REJECTED at RM-B.
3. As `demo-warehouse`, try **โอน** L-0001 from RM-A to RM-B, or **รับเข้า** at RM-A. Each shows
   "Lot นี้ถูก REJECTED ที่คลังใดคลังหนึ่ง …" and records nothing, although RM-A is RELEASED.
4. As `demo-production`, **เบิก** L-0001 to an order is refused the same way.
5. As `demo-approver`, **ส่งกลับ HOLD** on the REJECTED row (a reason is required). The transfer from
   step 3 now works.

`tests/inventory/test_rejected_lot_gate.py`, `test_rejected_lot_trigger.py` and
`tests/web/test_rejected_lot_screens.py` cover the same rules on PostgreSQL. A test that rejects a Lot
after inserting ledger entries in the same transaction calls `tests.quality.helpers.settle()` first,
because Django checks deferred constraints at teardown while production commits that history earlier.

## QC history (M6.4, Issue #113)

**ประวัติ QC** (`/quality/audit/`) lists every inspection and every disposition change at the
warehouses where the user holds QUALITY or APPROVER, newest first, in one read-only table (403
for anyone else; the nav link shows wherever **คุณภาพ** shows). Filters: warehouse (only the
user's) and from / to dates, inclusive, in local time (Asia/Bangkok). An invalid filter shows a
message and no rows. 50 rows per page; **เก่ากว่า →** opens the next older page. The admin also
lists `LotInspection`, view-only.

On the demo data (after `seed_production_demo --reset`, `set_demo_passwords`, `runserver`):
1. Log in as `demo-quality` or `demo-approver` and open **ประวัติ QC**: 14 rows, 7 inspections and
   their 7 HOLD → RELEASED events (L-0001, L-0002, L-0003, D-0001, L-0004, D-0002 INCOMING at RM-A;
   LED-BOARD-0001 FINAL at FG). Each event names the inspection it came from (`#n`).
2. Choose **คลัง** FG: the two LED-BOARD-0001 rows.
3. Record a FAIL on LAMP-0001 at FG on **คุณภาพ**, then return it as `demo-approver`: the newest
   rows are REJECTED → HOLD (demo-approver), HOLD → REJECTED and the FAIL inspection (demo-quality).
4. As `demo-warehouse` the page is refused (403).

`tests/web/test_quality_audit.py` and `tests/web/test_quality_admin.py` cover the same on
PostgreSQL; `tests/quality/test_qc_hardening.py` covers sample bounds, races and audit records.

## Evidence rule

CI (PostgreSQL 18.6, Python 3.14.8) is the evidence of record. Each run posts a summary with
the commit SHA, server version and test counts as a commit comment, and keeps one updated
comment on the PR, written by `scripts/ci_summary.py`. A local run on a different PostgreSQL
or Python version is a development check, not evidence.
While a PR is open, link to its CI comment instead of copying its SHA or counts into files;
those go into the post-merge docs PR (see AGENTS.md → Verification).

`ruff format --check .` runs in CI; run `uv run ruff format .` before committing.

A TDD RED result is valid only after dependency installation, Django settings, PostgreSQL
connectivity and test database creation succeed. Import errors, missing environment variables,
database connection failures, migration errors and SQLite runs are environment failures rather
than business-behavior evidence.
