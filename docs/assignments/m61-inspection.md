# M6.1 — Incoming/Final inspection and who decides

Repository `porntaned/ERP-for-Factory`; branch `claude/affectionate-hawking-eyr2d1`; base `main` `8b9c736`.
[Issue #96](https://github.com/porntaned/ERP-for-Factory/issues/96). Status: **spec approved by the owner (chat, 2026-11-06), PR 1 next**
("spec, awaiting owner review" held until then — historical). No product code yet.

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

Filled in during implementation: tested SHA, commands and results, CI comment. Review will be
self-review only (one agent, no sub-agents).
