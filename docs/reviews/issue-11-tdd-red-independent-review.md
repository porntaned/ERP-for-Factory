# Issue #11 — Independent TDD RED review

## Review identity

- Reviewer: `/root/m33_red_independent_review`
- Role: independent read-only Scrutinize reviewer
- Initial commit: `a3f4467ae0b87ebdcb490307607503bf41208c11`
- Re-reviewed commit: `78b2a8a8a00537ba70b9894e7443ddf792d91ee8`
- CI evidence: [Foundation #35](https://github.com/porntaned/ERP-for-Factory/actions/runs/39452581694)

## Intent and simpler alternative

The tests lock a typed, append-only HOLD/RELEASED history for the exact `(Lot, Warehouse)` pair.
A global Lot status cannot use the existing Warehouse-scoped permission boundary, while a generic
audit framework adds unrelated surface. The typed event is the smallest design that preserves the
required authorization and evidence.

## Findings and repair

The initial review returned `fix-then-ship`:

1. A deferred PostgreSQL foreign-key test did not reach the outer transaction boundary.
2. The contract did not exercise two concurrent direct inserts for the same event chain.
3. The contract did not prove a non-null, system-produced timestamp on a direct insert.

The test writer repaired the harness with `transaction=True`, added a two-connection direct-insert
race that requires one accepted event, and added the direct timestamp invariant. Ruff and collection
then passed with 244 total tests.

## Exact-commit verification

At `78b2a8a8a00537ba70b9894e7443ddf792d91ee8`, the reviewer traced all three repairs and found no
remaining blocker or major finding. CI confirmed PostgreSQL, checks, migrations and Ruff passed;
174 regression tests passed and all 70 new Quality tests failed only at the controlled missing-contract
boundary.

**Verdict: `ship` — the RED contract is ready for the implementer.**
