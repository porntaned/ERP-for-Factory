# Issue #26 — M4.1 stock ledger

- Repository: `porntaned/ERP-for-Factory`; [Issue #26](https://github.com/porntaned/ERP-for-Factory/issues/26).
- Branch: `codex/inventory/stock-ledger`; base `e806b6491d962f8124cc17d902eca2a692485ad1`.
- Manager/implementer/self-verifier: `/root`.
- Independent scope reviewer: `/root/m41_scope_review` (read-only).
- A separate test implementer `/root/m41_tests` was assigned but hit its usage limit
  before writing files. No delivered test work is attributed to that agent; root wrote tests.

## Intent and boundary

Implement M4.1's internal ledger and nonnegative invariant. The owner selected base-UOM
quantities with up to six fractional places. No conversion or unit-specific indivisibility
policy is claimed. Receipt, transfer, command idempotency, reversal, UI, valuation,
real data, stock-adjustment commands, merge and deployment are excluded.

The ledger is an infrastructure model, not an authorized business posting API. Synthetic
tests insert directly. Actor attribution is not authentication/authorization. Future
M4.2/M4.3 commands must check persisted active actor and exact Warehouse roles within
their transaction, and coordinate Quality eligibility under the shared Lot lock.
Missing disposition remains HOLD; M4.1 does not claim movement eligibility enforcement.

## Data contract

`StockLedgerEntry` retains protected Lot/Warehouse/actor, signed `quantity_delta`,
nonblank reason, database-generated identity/time. Pair must share an Organization.
Exact quantity is nonzero, finite, absolute value below `10^14`, representable with
six fractional places. Trailing zeros are harmless. Store unconstrained PostgreSQL
numeric via a small DecimalField subclass and explicit checks to prevent typmod rounding.
Balance is exact SUM per pair, zero if empty; a sum may exceed the single-entry range.
There is no editable balance cache, public write service, endpoint, form or admin action.

Database inserts lock Lot → Item → Warehouse → Plant in the existing Quality order;
the Lot lock serializes appends and parent SHARE locks protect the identity reads.
Reject writes outside READ COMMITTED: a fixed higher-isolation snapshot would make
lock-plus-SUM unsafe. Each accepted append leaves nonnegative stock. Transactions,
failed multirow statements and rollback retain all-or-nothing behavior.

Ordinary UPDATE/DELETE cannot rewrite history. Once history exists (even zero balance),
freeze Lot.item, Item.organization/base_uom, Warehouse.plant and Plant.organization.
Unrelated metadata and unreferenced identities remain editable. Ordinary explicit IDs
are rejected with GENERATED ALWAYS identity. Privileged override, TRUNCATE, disabling
triggers or database administration is outside the ordinary application-write boundary.

`get_stock_balance(lot=..., warehouse=...)` is an internal unauthenticated snapshot query.
Reject invalid, unsaved/manual-PK, missing and cross-Organization pairs with ValueError;
use persisted identities rather than cached relations. A returned balance is not a
reservation or authorization for a later write.

## Files, acceptance and evidence

In scope: inventory model/field/query/migration, inventory tests, issue-specific
assignment/review/evidence and prerequisite TASKS reconciliation. No dependencies,
existing Quality behavior, workflow or settings changes are planned.

Acceptance: controlled PostgreSQL RED after successful environment checks; real database
quantity/FK/identity/immutability/rollback and concurrency tests; lock-wait observations;
fresh migration/drift checks, relevant/full regressions; independent Scrutinize; owner-review PR.
Exact SHA, commands, environment, results and limitations must be recorded. M4.4 is not
complete merely because M4.1 tests concurrent nonnegative balance.

Two repair cycles per same finding; third recurrence escalates per MULTI_AGENT.

## Scope review

Reviewer traced existing models, Quality lock order and contracts at pre-branch HEAD
`6861058eb5663af2e0c59cd56224abcccfa5f935` (tree identical to base merge).
Initial verdict `fix-then-ship`: reject unsupported isolation and avoid decimal typmod
rounding. Both changes are incorporated above and in Issue #26 before implementation.
The reviewer recommended the small custom numeric field, explicit precision/range checks,
parent identity guards and ordinary-write vs authorization boundary. This is a design
review, not an implementation approval or PostgreSQL test execution.
