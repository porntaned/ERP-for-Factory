# Issue #29 — M4.2 synthetic receipt assignment

Repository: `porntaned/ERP-for-Factory`; [Issue #29](https://github.com/porntaned/ERP-for-Factory/issues/29).
Owner approved the three decisions in [the proposal](../proposals/m4.2-synthetic-receipt.md)
on 2026-10-23. Base `21ab14082fb18a99bfa1fb1c3a5061323bfadc33`, verified
PR #28 merge and [main CI #99](https://github.com/porntaned/ERP-for-Factory/actions/runs/39896584392).
Branch: `codex/inventory/synthetic-receipt`.

## Roles and files

- Root: manager, application implementer and CI observer/self-verifier. Owns
  inventory model/service/new migration, existing CI targeted step and batched docs.
- `/root/m42_contract_review`: separate read-only design reviewer; inspected ledger,
  Quality and authorization seams, recommended normalized receipt linkage, existing
  parent SHARE locks and savepoint covering both writes. No implementation blocker;
  no database execution or code edits claimed.
- `/root/m42_tests`: test implementer for `tests/inventory/test_stock_receipt.py`
  and `test_stock_receipt_concurrency.py`; shares working tree, no Git writes.
- `/root/m42_final_review`: separate final read-only source reviewer, inspected
  `0a96eda80107f088d043c0ed47683ae6e6ddbd69` against the base after GREEN; verdict
  `ship`. No independent PostgreSQL execution or CI retrieval claimed.

## Fixed contract

`receive_stock(*, lot, warehouse, actor, quantity: Decimal, reason: str,
request_id: UUID) -> StockReceipt`. Saved existing parents in one Organization;
strict positive finite Decimal below `10^14`, at most six fractional places
(trailing zeros allowed), nonblank exact reason. No new Lot/UOM conversion.

`StockReceipt` has unique UUID `request_id` and protected one-to-one `ledger_entry`.
Ledger supplies immutable payload and database time. Database rejects receipt
rewrites/deletion and missing/nonpositive ledger linkage; ordinary supplied receipt
IDs are rejected. Direct storage writes are not proof of business authorization.

Within READ COMMITTED: Lot UPDATE → Item SHARE → Warehouse SHARE → Plant SHARE →
persisted User UPDATE → exact destination WAREHOUSE grant UPDATE. Resolve parents
from locked persisted rows, recheck active User/grant even for retries; no other-role
or superuser bypass. Reject unsaved/manual-PK instances and invalid inputs.

Preserve current/default Quality state, including RELEASED; no Quality event write
or automatic release. Shared Lot lock coordinates with transitions. This existing-Lot
policy does not introduce per-delivery inspection or transfer/issue eligibility.

Same UUID plus exact actor/Lot/Warehouse/quantity/reason returns original receipt
after authorization; different payload conflicts. Global same-key races, including
different Lots, must leave one receipt/delta. Nested savepoint encloses BOTH ledger
append and receipt creation; outer rollback leaves neither.

## Acceptance and exclusions

Controlled real PostgreSQL RED; service/SQL constraint and rollback tests;
observed-blocker concurrency for retries, auth changes and Quality; fresh migration,
drift checks, targeted/relevant/full regressions; exact CI SHA/commands/environment;
independent final Scrutinize; PR for owner review. Keep M4.2 pending until owner merge.

No transfer/generic movement framework/full M4.4, reversal, UI/API/admin, demo,
adjustments, valuation, real data, full QC, Manufacturing, privileged operations,
dependencies, merge or deployment. Two repair cycles per same finding; third
recurrence escalates. Read independent context in parallel and batch evidence;
retain test → repair → independent review dependencies.

## Handoff

Root application implementation and test-agent delivery are committed at
`0a96eda80107f088d043c0ed47683ae6e6ddbd69`; test-only RED was `1571c6e`.
[Evidence](../evidence/issue-29-stock-receipt.md) records real CI commands/results:
87 receipt / 489 full tests passed. Independent source review is
[recorded separately](../reviews/issue-29-stock-receipt-independent-review.md).
Later changes are batched documentation only. Owner review/merge remains pending;
no deployment or other milestone implementation is included.
