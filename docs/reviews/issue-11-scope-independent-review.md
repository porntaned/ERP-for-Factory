# Issue #11 independent scope review

## Review target

- Repository: `porntaned/ERP-for-Factory`
- Base commit: `6f6e06b`
- Proposed task: M3.3 Audit and minimum Released/Hold state
- Reviewers: `/root/m33_scope_architect`, `/root/m33_risk_reviewer`, `/root/m33_test_contract`
- Mode: independent read-only Scrutinize before TDD or implementation

## Intent

Provide the smallest auditable HOLD/RELEASED foundation that can later inform Inventory movement
eligibility without claiming that inspections or stock movements already exist.

## Simpler-alternative pass

A mutable global status on `inventory.Lot` is smaller in columns but cannot be authorized safely:
Lot has no Warehouse while every operational role grant is tied to one exact Warehouse. A generic
audit table or model signals would add broad surface and could miss direct or bulk database writes.
The smaller defensible behavior is one typed history scoped to an exact Lot and Warehouse.

## Findings

### Blocker — a global Lot status has no valid Warehouse authorization path

**Why it matters:** A Quality user in one Warehouse could change state that silently affects the
same Lot in another Warehouse.

**Evidence:** `inventory.Lot` contains only Item and code, while `WarehouseRoleAssignment` and
`has_warehouse_role` evaluate one exact Warehouse. The repository also assigns Quality ownership of
inspection decisions and Inventory ownership of movement eligibility.

**Required change:** Scope disposition and history to `(lot, warehouse)`, require the exact
Warehouse `QUALITY` grant, and reject cross-Organization pairs.

### Major — M3.3 must not claim the later Quality or Inventory workflows

**Why it matters:** Inspection records begin in M6 and stock ledger behavior begins in M4. Claiming
either now would create an unverified integration and duplicate later ownership.

**Required change:** Limit Issue #11 to the decision state/history and transition/query interfaces.
Exclude inspections, stock quantities and movement enforcement.

### Major — audit integrity must survive direct PostgreSQL access and concurrency

**Why it matters:** Application-only `save()` checks can be bypassed by queryset updates, deletes,
raw inserts and competing callers, leaving false or rewritten history.

**Required change:** Test and enforce valid state transitions, chain integrity, immutability,
idempotent retries, protected references and serialized concurrent transitions on PostgreSQL.

## Verification contract

The RED suite must exercise missing-state-as-HOLD, valid transitions, exact-Warehouse Quality
authorization, inactive/anonymous/unsaved and wrong-scope callers, same-Organization validation,
invalid/no-op/stale inputs, required reason, retry conflicts, atomic rollback, concurrent decisions,
protected deletion, forged chains and direct UPDATE/DELETE rejection. Existing tests must remain
GREEN while new tests fail only because the locked contract is absent.

## Verdict

`rework`, then proceed: the original checklist wording was underspecified; Issue #11 now narrows it
to a Warehouse-scoped Lot disposition history with explicit authorization and PostgreSQL integrity.
