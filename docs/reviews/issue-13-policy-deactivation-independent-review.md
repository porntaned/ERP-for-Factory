# Issue #13 — Independent Scrutinize

- Reviewer: `/root/issue13_independent_review`, separate read-only agent.
- Reviewed implementation SHA: `abe63e154de62e7d37f3ff4c47252f6a88c07587`.
- Base: `9b1d182eb6867b70f076e95a63dc03f1814f00ec`.
- Scope: audit Finding 1 only. Manager transcribed the review; reviewer did not edit implementation.

## Intent and simpler alternative

Deny persisted inactive users through both Warehouse policies despite a retained active
Python instance. Two predicates in the existing queries suffice. Extra user lookups,
locks or service changes would enlarge scope without improving this read contract.

## Traces and verification

- Boolean path: `access_control/policies.py:40` -> unchanged role/user/warehouse guards ->
  assignment filter at line 54, including `user__is_active=True` at line 56 -> `exists()`.
  A persisted inactive user no longer has a matching result.
- QuerySet path: `access_control/policies.py:62` -> unchanged guards -> single filter at
  line 67 including `role_assignments__user__is_active=True` at line 69 -> `distinct()`.
  User ID, active status and role constrain the same joined grant. Construction remains
  lazy; deactivation before evaluation excludes the warehouse.
- `tests/access_control/test_persisted_deactivation.py:9`, `:29`, `:49` use real saved
  users/grants and database UPDATEs, retaining stale active objects. Each proves initial
  access. The third checks zero queries during construction and denial after deactivation.
- Existing isolation, role validation and duplicate prevention tests remain in
  `tests/access_control/test_warehouse_role_policy.py`.
- Reviewer independently fetched RED job `119107957640`: **3 failed, 261 passed in 4.55s**.
- Reviewer independently fetched GREEN run `39566040200`, job `119108431491`:
  **targeted 3 passed in 0.46s; full 264 passed in 3.27s**. PostgreSQL 18.6,
  Python 3.14.8, Django 5.2.18, psycopg 3.3.6. Django checks, migration drift,
  fresh migrations and Ruff passed. [Commands and links](../evidence/issue-13-policy-deactivation.md).
- Reviewer inspected actual GitHub logs, not a separate local PostgreSQL execution.

## Findings and boundaries

No blocking findings within Issue #13. No repair cycle required.
Already-evaluated QuerySet caches and check-then-write races are outside this policy-read
contract. Quality's actor/grant locking at `quality/services.py:115` remains unchanged.
Finding 2 (unsaved manual-PK users), event IDs and other audit findings remain outstanding.
GREEN here does not resolve those findings.

**Verdict: ship — Finding 1 is fixed minimally and verified on PostgreSQL; proceed to
owner-review PR, with no merge or Finding 2 work.**
