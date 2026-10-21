# Issue #11 — Independent implementation Scrutinize

## Review identity

- Reviewer: `/root/m335_independent_review`, separate from the implementer; read-only review.
- Initial reviewed SHA: `0c2b2e129d1f136c88410a600b076a597db2962a`.
- Initial CI: [Foundation #40](https://github.com/porntaned/ERP-for-Factory/actions/runs/39527309664), PostgreSQL 18.6, `244 passed in 3.66s`.
- Method: [Scrutinize](../SCRUTINIZE.md), recorded by `/root` from the reviewer's findings.
- Repair agent: `/root/m335_repair`.

## Intent and simpler alternative

Record an attributable, append-only HOLD/RELEASED decision for an exact Lot/Warehouse pair,
enforcing current QUALITY authorization and same-Organization scope. A typed history fits this
boundary; global Lot status or a generic audit framework would weaken it. Keep the architecture
and repair the integrity seams.

## Initial findings

The locations below refer to the initial reviewed SHA, before repair.

### P1 — An accepted HOLD can be hidden by event ID order

- Finding: `quality/migrations/0001_initial.py:142` reads the highest event ID but accepts a new
  event without requiring a higher ID; `quality/services.py:87` also reads by descending ID.
- Why it matters: an accepted HOLD decision can still be reported as RELEASED.
- Evidence: insert ID 100, HOLD → RELEASED; then ID 50, RELEASED → HOLD. The trigger accepts
  the second event but the getter still reads ID 100. Sequence allocation before the Lot lock
  is not an authoritative append order either.
- Suggested change: enforce authoritative increasing order under the Lot lock and add a
  deterministic descending-ID PostgreSQL regression.

### P1 — Authorization can be stale before the append

- Finding: `quality/services.py:107` checks permission before the transaction/Lot lock;
  `access_control/policies.py:31` uses the caller's cached `is_active` value.
- Why it matters: a deactivated user or a grant revoked while waiting can still authorize a decision.
- Evidence: keep an active User instance, deactivate its persisted row through another instance,
  then submit with the stale instance and retained QUALITY grant. No later persisted-user check
  rejects it. Likewise, there is no grant recheck after waiting for the Lot lock.
- Suggested change: after the Lot lock, lock/check the persisted active User and exact QUALITY
  assignment through the append. Test stale User state and revocation during a lock wait.

### P2 — Parent reassignment can change the meaning of immutable history

- Finding: `inventory/models.py:8`, `catalog/models.py:26`, `facilities/models.py:20` and `:38`
  permit identity/scope reassignment; the event trigger validates only INSERT.
- Why it matters: a RELEASED history can refer to another material or become cross-Organization
  without any event being edited.
- Evidence: after release, update the Lot's Item or move the Warehouse to another Organization's
  Plant. PROTECT prevents deletion, not reassignment.
- Suggested change: guard the referenced identity/scope edges at the database boundary and add
  direct-update regressions, while leaving unrelated metadata and unreferenced records editable.

## Trace coverage and initial verdict

The reviewer traced missing-history HOLD, pair filtering, expected state, retry payload comparison,
global UUID uniqueness/conflict recovery, invalid/no-op input, server time, direct state/reason
constraints, protected deletion, append-only triggers, same-Organization inserts and the original
three concurrency tests. Existing GREEN covered those tests; the new counterexamples were static
traces at this review stage, not additional PostgreSQL executions by the reviewer.

Initial verdict: **fix-then-ship — accepted event ordering can hide a recorded HOLD.**

## Repair and independent re-review

- Production repair: `6253fd205c879a70c7884a338ce51f53ecac3c7a`.
- Final independently reviewed SHA: `44b466fdd4e9d0134564c77aef7a316c1a2b8b7e`.
- Reviewer: `/root/m335_independent_review`, read-only exact-commit re-review.
- PostgreSQL verification: [Foundation #42](https://github.com/porntaned/ERP-for-Factory/actions/runs/39528381765),
  [job logs](https://github.com/porntaned/ERP-for-Factory/actions/runs/39528381765/job/118988295071),
  `261 passed in 4.54s`, PostgreSQL 18.6, fresh migrations, no drift and Ruff passed.

1. `quality/migrations/0002_preserve_history_identity.py:24` locks the Lot before reading history;
   `:47` rejects event IDs at or below the latest ID. The descending-ID test asserts that exact
   trigger error and confirms the next accepted HOLD is returned by the getter.
2. `quality/services.py:108` locks the Lot, reloads/locks the persisted User and exact QUALITY
   assignment, and checks persisted active status before resolving retry or appending. Tests cover
   stale User state and revocation during an observed PostgreSQL Lot-row lock wait.
3. `quality/migrations/0002_preserve_history_identity.py:24` locks identity parents; `:69` onward
   guards the four referenced identity edges. Tests cover sequential and waiting-concurrent updates
   for all four edges, allowed unreferenced changes, and allowed metadata/unchanged-edge updates.
4. `tests/quality/test_postgresql_constraints.py:55` reverses/reapplies migration 0002 and verifies
   that the original/v2 insert trigger is restored in each direction.

The first repair CI [#41](https://github.com/porntaned/ERP-for-Factory/actions/runs/39527989960)
reported 259 passed / 2 failed because two allowed-reassignment fixtures collided with existing
Warehouse/Plant codes. The final test-only repair uses empty target Organizations/Plants and asserts
the specific identity/order trigger messages, so uniqueness errors cannot falsely satisfy rejection
tests. CI #42 then passed the original 244 cases plus 17 new regressions.

The independent reviewer traced all three fixes and the final fixture repair at exact SHA
`44b466f`; no new material findings remain. The manager fetched/verified CI logs and supplied that
execution evidence to the reviewer. The reviewer did not run PostgreSQL locally.

Out-of-order direct IDs now fail explicitly with IntegrityError. Direct database writes do not
enforce application role authorization; privileged trigger bypasses and every possible transaction
schedule are outside this review. Stock/inspection/UI behavior remains outside this issue.

**Final verdict: ship — the decision-order, current-authorization and identity-integrity defects
are repaired and the exact reviewed commit is GREEN.** Owner merge/deploy authorization is separate.
