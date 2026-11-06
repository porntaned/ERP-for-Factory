# M6.1 — Incoming/Final inspection and who decides

Repository `porntaned/ERP-for-Factory`; branch `claude/affectionate-hawking-eyr2d1`; base `main` `8b9c736`.
[Issue #96](https://github.com/porntaned/ERP-for-Factory/issues/96). Status: **PR 1 merged ([PR #97](https://github.com/porntaned/ERP-for-Factory/pull/97) at `e7f64e7`); PR 2 (web) in [PR #101](https://github.com/porntaned/ERP-for-Factory/pull/101), awaiting CI** (2026-11-06; "PR 2 (web) next" held until then — historical)
("PR 1 implemented, PR awaiting owner review", "spec approved by the owner, PR 1 next" and "spec, awaiting owner review" held until then — historical).
Plan: [`m61-plan.md`](m61-plan.md).

## Purpose

Today a QUALITY user can move a Lot-Warehouse between HOLD and RELEASED with
`quality.services.transition_lot_disposition`. The command needs only a reason. Nothing records what
was inspected or what the result was, and a failed Lot has no state of its own. M6.1 adds an
inspection record that is the only way to release or reject a Lot.

## Owner rulings (chat, 2026-11-06)

1. **A failed inspection makes the Lot-Warehouse `REJECTED`**, a new disposition. Scrap and return to
   supplier are out of scope.
2. **QUALITY at the warehouse inspects and decides in one command:**
   - PASS → `RELEASED`
   - FAIL → `REJECTED`
3. **An inspection is a header record only.** There is no checklist or template. If needed, that will
   be a separate Issue.
4. **HOLD → RELEASED and HOLD → REJECTED happen only through an inspection.** The command and
   PostgreSQL both enforce this.
5. **REJECTED → HOLD needs an APPROVER at that warehouse and a reason.** The APPROVER must not be the
   inspector who rejected the Lot. The Lot can then be inspected again. History stays.
6. **The inspection kind comes from the Lot's origin.** The user does not choose it (see Data).
7. **Two PRs:**
   - PR 1: model, commands, database rules and demo data
   - PR 2: web screens, following the M5.5 pattern

## Scope

In:
- PR 1 as listed in ruling 7.
- PR 2: a list of HOLD Lot-Warehouses per warehouse, an inspection form, the inspection history
  of a Lot, and a "ส่งกลับ HOLD" button for APPROVER on REJECTED rows.

Out:
- checklist templates
- scrap or return to supplier
- valuation
- refusing a REJECTED Lot at *other* warehouses: this is M6.2, as the owner ruled during the M5.2
  scrutinize
- traceability views (M6.3)
- Deploy

## Current behaviour this builds on (checked in code)

- **Disposition is per Lot + warehouse.**
  - `quality.services.get_lot_disposition` returns the latest `LotDispositionEvent.to_disposition`,
    or `HOLD` when there is no event.
  - So a Lot arrives `HOLD` at a warehouse it was never released at, including a transfer
    destination. Each such Lot-Warehouse needs its own inspection.
- **Inventory already gates on `RELEASED` at the moving side.** All three refuse when that side is
  not `RELEASED`, which includes `REJECTED`:
  - `inventory/transfer_policy.py`: transfer source
  - `inventory/transfers.py`: the production gate used by `manufacturing.services` issue and return
  - `inventory/reversals.py`: transfer reversal, at the original destination
  - No Inventory or Manufacturing code changes. Tests prove the behaviour.
- **Lot origin is not stored on the Lot.**
  - A receipt is `inventory.StockReceipt` → `StockLedgerEntry(lot=…)`.
  - A production output is `inventory.ProductionPosting(kind="OUTPUT")` → `StockLedgerEntry(lot=…)`.
  - Output Lots are created new by `manufacturing.services._output_lot` and belong to one order.
  - Nothing prevents a later receipt into an output Lot's code.
- **Existing database rules on `quality_lotdispositionevent`:**
  - append-only (migration 0001)
  - the insert trigger `quality_validate_lot_disposition_insert_v2` (0002) checks the organization
    and that `from_disposition` equals the current state
  - the key registers as `DISPOSITION` in the shared registry, last (0004, 0005)
  - `from`/`to` are `varchar(8)`, so `REJECTED` fits

## Data (PR 1)

**`LotDisposition`** gains `REJECTED`. The check constraints on `from_disposition` and
`to_disposition` follow `LotDisposition.values`.

**`quality.LotInspection`** (new, append-only):

| Field | Rule |
|---|---|
| `lot`, `warehouse` | same organization (as events) |
| `kind` | `INCOMING` or `FINAL`, derived (below) |
| `result` | `PASS` or `FAIL` |
| `sample_quantity` | positive, at most six decimal places, below 10^14 (`inventory.quantities.is_valid_quantity`); not above the Lot's balance at that warehouse |
| `note` | nonblank |
| `inspector` | the actor |
| `created_at` | statement time, set by the database |

`kind` derivation:
- `FINAL` if the Lot has any `ProductionPosting` of kind `OUTPUT`
- otherwise `INCOMING` if it has any `StockReceipt`
- otherwise the command refuses: there is nothing to inspect

A Lot with both an OUTPUT and a receipt is `FINAL`.

**`LotDispositionEvent.inspection`**: a new nullable one-to-one to `LotInspection`.
- An event that leaves `HOLD` carries its inspection.
- Every other event has none.
- The inspection has no request key of its own. The command's `request_id` is the event's existing
  key, registered as `DISPOSITION`, so the shared registry does not change.

## Commands (PR 1, `quality/services.py`)

### `record_inspection(*, lot, warehouse, result, sample_quantity, note, actor, request_id)`
- **Authority:** an active user with QUALITY at `warehouse`. The command checks this under the same
  locks as today: Lot, then actor, then grant.
- **Refusals** (nothing written):
  - the Lot and warehouse are not saved or not in one organization
  - `result` is not PASS or FAIL
  - `sample_quantity` is invalid or above the balance
  - `note` is blank
  - `request_id` is not a UUID
  - the current disposition is not `HOLD`
  - the Lot has no origin
- **Effect:** in one transaction, create the `LotInspection` and then the event with
  `from = HOLD` and `to = RELEASED` (PASS) or `REJECTED` (FAIL), linked to it. Return the inspection.
- **Replay:** the same `request_id` with the same Lot, warehouse, actor, result, quantity and note
  returns the first inspection. Any other use of the key is a conflict, as is a key owned by another
  command. This follows `_resolve_existing_request` and `owned_by_other_command`.

### `transition_lot_disposition` (narrowed)
- Allows only `RELEASED → HOLD` (QUALITY, reason).
- Any other pair is refused with a message that names the right command.
- Replay is unchanged.

### `return_rejected_to_hold(*, lot, warehouse, actor, reason, request_id)`
- **Authority:** an active user with APPROVER at `warehouse`. The actor must not be the inspector of
  the inspection that rejected this Lot-Warehouse.
- **Refusals:** the current disposition is not `REJECTED`; the reason is blank; the actor is the
  inspector.
- **Effect:** an event `REJECTED → HOLD` with the reason and no inspection.
- **Replay and conflict:** as above.

## PostgreSQL rules (PR 1, new quality migration)

All checks run on insert or on the transition, so history written before M6.1 stays valid. This
follows the approach of manufacturing migration 0008.

1. **Inspection rows:**
   - organization match
   - kind matches the Lot's origin, with the same derivation as the command
   - `sample_quantity` is valid
   - the note is nonblank
   - append-only: no UPDATE or DELETE
2. **Inspection and event come together.** A deferred constraint trigger, run at commit, checks that
   every new inspection is referenced by exactly one event, on the same Lot and warehouse.
3. **Event rules:**
   - An event `HOLD → RELEASED` or `HOLD → REJECTED` must reference an inspection.
     - PASS must go to `RELEASED`; FAIL must go to `REJECTED`.
     - It must be on the same Lot and warehouse.
   - An event that references an inspection must be one of those two.
   - An event without an inspection may only be `RELEASED → HOLD` or `REJECTED → HOLD`.
   - `REJECTED → HOLD` needs an APPROVER grant at the warehouse, and its actor must differ from the
     rejecting inspector.
4. **The existing chain and organization checks stay.** The key registration trigger still fires last.

## Demo data

- `seed_demo` and `seed_production_demo` release their RM-A Lots with `record_inspection`
  (INCOMING, PASS, sample 1, a synthetic note). They use deterministic keys as now.
- Output Lots stay `HOLD`.
- `--reset` gives the same end state as today.
- Rerunning on a database seeded before M6.1 is not supported for the release step: the old key
  belongs to an event without an inspection. Run it with `--reset`. The spec states this; the code
  does not try to repair it.

## Tests (written first; RED before code)

**Commands:**
- PASS → RELEASED, FAIL → REJECTED
- kind is INCOMING for a receipt Lot, FINAL for an output Lot (including mixed), refused for a Lot
  with no origin
- refusals: blank note, bad quantity, quantity above the balance, not HOLD, no QUALITY grant,
  another warehouse's grant
- replay returns the same record; key conflicts; a key used by another command

**Narrowed command:**
- `transition_lot_disposition` HOLD → RELEASED is refused
- RELEASED → HOLD still works

**Return to HOLD:**
- APPROVER succeeds
- the inspector, even with APPROVER, is refused
- QUALITY only is refused
- after the return, a new inspection can release the Lot

**Database, by direct SQL:**
- an event out of HOLD without an inspection is refused
- an inspection whose result does not match the event is refused
- an inspection without an event fails at commit
- the wrong kind is refused
- UPDATE or DELETE of an inspection is refused
- REJECTED → HOLD by a non-APPROVER, or by the inspector, is refused

**Effects:**
- a REJECTED Lot-Warehouse cannot be transferred, issued to production, or used as the destination
  side of a transfer reversal

**Migrations:**
- the new migration unapplies and reapplies

**Regression:**
- existing tests that release with `transition_lot_disposition` move to `record_inspection`
  (18 call sites under `tests/`)
- `seed_demo` and `seed_production_demo` produce the same balances

## Rulings confirmed (owner, chat, 2026-11-06; were "to confirm before code")

1. **A Lot with both a production OUTPUT and a receipt is inspected as FINAL.** This is a rare case:
   it needs a receipt typed against an output Lot's code.
2. **`sample_quantity` may not exceed the Lot's balance at that warehouse.** The alternative is any
   positive quantity.
3. **`note` is required**, also for PASS. The alternative is required for FAIL only.

## PR split

- **PR 1:** this spec, model, migration, commands, demo data, tests, and docs:
  - `docs/TASKS.md`
  - this file
  - `docs/DEVELOPMENT.md` demo steps if they change
- **PR 2:** web screens. It gets its own short design before code.

## Evidence and review

Recorded in "PR 1 — delivered" below ("filled in during implementation" — historical, 2026-11-06).
Review is self-review only (one agent, no sub-agents).

## PR 1 — delivered (2026-11-06)

| Area | Files |
|---|---|
| Model | `quality/models.py`: `LotDisposition.REJECTED`, `InspectionKind`, `InspectionResult`, `LotInspection`, `LotDispositionEvent.inspection` |
| Database | `quality/migrations/0006_lot_inspection.py` (schema; kind matches origin; append-only; each inspection linked by its event at commit), `0007_inspection_transition_rules.py` (only an inspection leaves HOLD; REJECTED → HOLD needs an APPROVER who is not the rejecting inspector) |
| Commands | `quality/services.py`: `record_inspection`, `inspection_kind`, `return_rejected_to_hold`; `transition_lot_disposition` now only RELEASED → HOLD |
| Demo data | `seed_demo`, `seed_production_demo`: RM-A Lots released by a passing INCOMING inspection, same keys |
| Tests | `tests/quality/test_inspection.py` (34), `tests/quality/helpers.py`; existing callers moved off the old release path |

Commits: `24a06f8` (Task 1), `f240747` (Task 2), `2185311` (Task 3), `0044be1` (Task 4), then docs.

### RED / GREEN

1. **Task 1:** RED at collection (`LotInspection` missing); GREEN 17. The full suite then showed 14
   legacy failures: migration tests wrote through the live model at old schemas, and pending
   deferred triggers blocked `ALTER TABLE`. Fixed (rulings 1–2); 969 passed.
2. **Task 2:** the two Review Focus tests passed at once (guards). Callers moved; 971 passed.
3. **Task 3:** RED 10 (missing command; old pairs accepted; raw event accepted); GREEN 31. Closing the
   old path broke 38 Issue #11-era tests, all rewritten (rulings 4–7); 983 passed.
4. **Task 4:** three guards passed at once. The issue guard first failed for the wrong reason
   (BOM limit) and moved to a fixture with nothing issued; 986 passed.

### Rulings made while building

1. **Legacy migration tests** (`tests/quality/test_event_identity_migration.py`,
   `tests/inventory/test_request_key_migration.py`) write through the historical model of the
   schema they migrate to. Two live-command calls at schema 0003 became historical inserts.
2. **Migration 0006 runs `SET CONSTRAINTS ALL IMMEDIATE`** before and after its schema change, so
   pending deferred checks fire first in both directions. This is the pattern of inventory 0008
   and 0009.
3. **Tests-only helpers** (`tests/quality/helpers.py`, owner ruling 2026-11-06):
   - `release`: the normal path, through `record_inspection`
   - `force_release`: writes an inspection and event directly for setups the command cannot
     reach (a pair with no stock); the database still checks origin, kind and pairing
   - `give_origin`, `made_receipts`, `ensure_origin`, `raw_inspection`
4. **Quality's own contract tests** for `transition_lot_disposition` now exercise RELEASED → HOLD
   after a setup release.
5. **Direct-insert tests** attach a matching inspection. Tests whose insert must fail build it in
   the same atomic block, because Django's test teardown runs `check_constraints`.
6. **Identity-reassignment tests** now match "identity cannot be reassigned". An inspected Lot has
   stock history, so the inventory guard fires first with its own message; reassignment is still
   refused.
7. **Quality concurrency tests** race `record_inspection`, which leaves HOLD; the serialization they
   check is unchanged.
8. **The REJECTED → HOLD trigger checks the APPROVER grant but not `is_active`**, like the earlier
   Quality triggers. The command checks both.

### Verification (development check, not evidence of record)

PostgreSQL 16.15 (Ubuntu), Python 3.14.6 (the pin 3.14.8 is not available in this sandbox).
Tested commit `0044be181671331b47383398540314ab1c7a9531`; the later commit changes docs only.

| Command | Result |
|---|---|
| `uv run --env-file .env pytest -q` | 986 passed |
| `uv run ruff check .` / `ruff format --check .` | clean |
| `makemigrations --check --dry-run` | No changes detected |
| `seed_production_demo --reset`, then again | 4 INCOMING PASS inspections at RM-A (L-0001..3, D-0001), all RELEASED; output Lots HOLD; rerun adds nothing |

Demo walk on a disposable database (shell, after `seed_production_demo --reset`):
- `demo-quality` has no QUALITY grant at FG, so FINAL inspection of LAMP-0001 was refused
  (`DispositionAuthorizationError`); see finding 1.
- With walk-only grants (QUALITY and WAREHOUSE at FG):
  - FAIL gives FINAL and REJECTED
  - a transfer out of FG gets `TransferQualityError`
  - return to HOLD by `demo-quality` gets `DispositionAuthorizationError` (no APPROVER)
  - return by `demo-approver` gives HOLD
  - PASS gives RELEASED
- The database was dropped afterwards.

### Scrutinize (self-review, `docs/SCRUTINIZE.md`)

**Intent:** release and reject a Lot only through a recorded inspection, with a separate APPROVER to
undo a rejection. A smaller change (a note on the old command) would not give the database a rule
to enforce, so it does not meet ruling 4.

**Traced:**
- `record_inspection` locks in this order: Lot, actor, grant, then reads replay, kind, state and
  balance, then inserts the inspection and the event. The inserts' triggers take the same Lot lock,
  then Item, Warehouse and Plant shares, then the key registry. This is the same order as the old
  transition; receipts and transfers also lock the Lot first, so the balance read is stable
  (`test_concurrent_inspections_one_wins`, the receipt race in
  `tests/inventory/test_stock_receipt_concurrency.py`).
- Origin cannot change underneath: an OUTPUT posting creates a new Lot, and a receipt into an
  existing Lot takes the Lot lock.
- Deferred pairing: the command writes both rows in one atomic block. An orphan fails at commit
  (`test_orphan_inspection_fails_at_commit`, `transaction=True`).
- Replay is checked before state, so an exact retry after a later change still returns the first
  record. A key owned by another command conflicts (`test_replay_and_conflicts`).
- Gates: transfer source, production issue/return and transfer reversal all require RELEASED, so
  REJECTED is refused there (Task 4 tests). REJECTED at *other* warehouses is still allowed by
  design (M6.2).
- Inputs: Unicode notes (Thai and em dash in tests); the quantity is bounded by
  `is_valid_quantity` and the check constraint; a blank note, zero, negative and seventh decimal
  place are all refused.
- No web or admin path writes dispositions. The admin registers `LotDispositionEvent` read-only;
  the web reads `get_lot_disposition` and already renders REJECTED.

**Findings:**
1. *Minor:* the demo seed grants `demo-quality` QUALITY only at RM-A, so FINAL inspection cannot be
   shown with demo users. Adding grants is a privileged-access change, so it is left for the owner
   to decide, before PR 2.
2. *Minor:* `LotInspection` is not in the read-only admin. It is optional; PR 2 adds screens.
3. *Minor:* the database does not check that the approver is active (ruling 8).

**Verdict:** `ship`. Every rule in the spec is enforced in the command and in PostgreSQL, the gates
need no change, and the open items are minor.

### PR 1 closeout (2026-11-06)

PR CI [#239](https://github.com/porntaned/ERP-for-Factory/actions/runs/42189537981) on head `869ad1e` (tested as merge `df2a135`): PostgreSQL 18.6, Python 3.14.8, **986 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/97#issuecomment-6680899302)). The owner approved the merge in chat; [PR #97](https://github.com/porntaned/ERP-for-Factory/pull/97) merged at `e7f64e7ca0070c7c84508950bc66c86c503c71c1`; [main CI #240](https://github.com/porntaned/ERP-for-Factory/actions/runs/42190005568): PostgreSQL 18.6, **986 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/commit/e7f64e7ca0070c7c84508950bc66c86c503c71c1#commitcomment-208439236)). Review remained self-review only. Issue #96 stays open for PR 2. Open owner decision before PR 2: whether the demo seed grants `demo-quality` QUALITY at FG (finding 1).

## PR 2 — design and owner rulings (chat, 2026-11-06)

The owner approved this short design before code, and both demo grants (a privileged-access change
for synthetic users, AGENTS.md):

- `/quality/`: HOLD and REJECTED Lot-Warehouses with stock, at warehouses where the user holds
  QUALITY or APPROVER (403 otherwise; nav link only for them).
- Inspect form for QUALITY on HOLD rows → `record_inspection`; "ส่งกลับ HOLD" for APPROVER on
  REJECTED rows → `return_rejected_to_hold`. POST-only, hidden request UUID, command errors as
  messages.
- Lot genealogy page: inspection history and disposition history.
- Demo grants: `demo-quality` QUALITY at FG; `demo-approver` APPROVER at FG.
- Reviewed by a fresh sub-agent before merge.

## PR 2 — delivered (2026-11-06)

- `demo/quality_views.py`, `demo/quality_forms.py`, `demo/templates/demo/quality/list.html`;
  genealogy tables `inspections` and `dispositions`; nav "คุณภาพ"; routes `quality-list`,
  `quality-inspect`, `quality-return`.
- `seed_demo` grants `demo-quality` QUALITY at FG. `demo-approver` APPROVER at FG comes from
  `seed_production_demo` (ruling after review m1: it already granted it, and it is the seed that
  creates FG Lots; adding it to `seed_demo` only opened a reverse-output button with no FG Lots).
- `quality.services.rejecting_inspector_id` is public, so the screen hides the return button from
  the rejecting inspector (review m2).

### RED / GREEN

- 11 screen tests failed first (no routes, no grants), then passed.
- Review fixes: m2, m3 and m6 tests failed first, then passed; CSRF and no-role tests passed at once
  (coverage). Total 17 tests in `tests/web/test_quality_screens.py`.

### Verification (development check, not evidence of record)

PostgreSQL 16.15, Python 3.14.6, commit `3a9c0c4`: full suite 1003 passed; Ruff check and format
clean; no pending migrations (no schema change).

### Review

**Independent** review by a separate sub-agent with a fresh context, read-only, on `38d7d45`:
verdict fix-then-ship, no blocker — [m61-pr2-independent-review.md](../reviews/m61-pr2-independent-review.md).
Findings M1, m1–m3, m5, m6 fixed in one pass; m4 (per-row queries) deferred. The fixes were not
re-reviewed; tests and CI cover them.
