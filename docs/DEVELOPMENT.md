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

Local PostgreSQL 18.6 must already be reachable using the values in `.env`.

```powershell
Copy-Item .env.example .env
# Replace every placeholder in .env before continuing.
uv sync --locked --all-groups
uv run --env-file .env python manage.py check
uv run --env-file .env pytest
uv run ruff check .
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
the real commands. The result can be read in the shell below or on the M5.5 screens ("no screens yet (M7)" was true until M5.5 — historical, corrected 2026-11-06).
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
o = ProductionOrder.objects.get()
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

## Quality inspection (M6.1, shell)

Only an inspection moves a Lot-Warehouse out of HOLD: PASS → RELEASED, FAIL → REJECTED. The kind
(INCOMING or FINAL) follows the Lot's origin. The sample may not exceed the balance there, and the
note is required. A REJECTED pair returns to HOLD only through an APPROVER who is not the rejecting
inspector.

**On the web (M6.1 PR 2):** after `seed_production_demo --reset`, `set_demo_passwords` and
`runserver`:
1. Log in as `demo-quality` and open **คุณภาพ** (`/quality/`). LAMP-0001 (5) and LAMP-0002 (4) are
   HOLD at FG.
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
