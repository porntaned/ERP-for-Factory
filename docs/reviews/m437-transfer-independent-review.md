# M4.3.7 independent source review

Reviewer: separate native agent `/root/m437_independent_review`.
Reviewed SHA: `c62dc81a9cf4a2a19b2975582dcbd49a3565eec6`.
Base: `e8ad707b86f7c613c3db291fd6dcabd3f491a569`.
Repository/branch: `porntaned/ERP-for-Factory`, `codex/inventory/transfer-readiness`.
Review performed after [Foundation #133](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067756440)
passed. Root records the separate reviewer's returned report below; reviewer edited no files.

## Findings and trace

No actionable defect found in M4.3.7 or the transfer seams reviewed.

- [Workflow test](../../tests/inventory/test_transfer_workflow.py), lines 20–117:
  real receipt -> default HOLD rejection -> Quality release -> transfer -> linked history
  -> exact replay/conflict -> revoked-grant denial. Both destination states, fractional
  quantities and preserved Unicode reasons are meaningfully asserted.
- [Transfer command](../../inventory/transfers.py), lines 57–149, and
  [scope/Quality gate](../../inventory/transfer_policy.py), lines 28–101:
  exact payload validation, persisted identities, PostgreSQL READ COMMITTED, parent
  locks, current actor/both grants, authorization before replay, source Quality/balance
  checks, atomic debit/credit/history, and losing UUID race rollback.
- [Inventory services](../../inventory/services.py), lines 16–166, and
  [Quality services](../../quality/services.py), lines 84–179: balance aggregation,
  receipt authorization/deduplication and shared Lot serialization with Quality transitions.
- Models/field and migrations 0002–0006: exact numeric constraints, nonnegative balance
  trigger, parent identity/lifetime protection, immutable ledger/history, consistent
  transfer links, receipt/transfer credit ownership exclusion, database identity/time,
  nullable legacy UUIDs and unique requests.
- Existing atomic, Quality, history and request tests, including actual PostgreSQL
  blocking detection in `blocked_action`/`wait_for_lock`, rollback, competing debits,
  authorization/Quality serialization, UUID races and migration preservation.

## Simpler alternative and verdict

The tests-and-evidence-only solution is appropriate; no production behavior or
dependency change is needed. CI simply adds an explicit targeted workflow step.

Verdict: **ship**. The real command path and its database/concurrency seams are covered
without expanding policy or implementation scope. No repair cycle was required.

## Limits

Independent **source review**, with no independent runtime execution or GitHub inspection.
Foundation #133 PostgreSQL 18.6 results were supplied by root and are not independently
verified by this reviewer. No UI/API, M4.4, reversal, production scale/load or privileged
SQL review is claimed. Later documentation-only reconciliation is outside the reviewed
SHA. Reviewer performed no external actions; owner acceptance/merge remains separate.
