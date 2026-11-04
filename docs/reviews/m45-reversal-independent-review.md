# Independent review — M4.5 reversal (`28d8d30..b02dda9`)

Reviewer: separate read-only agent, 2026-11-04, following [Scrutinize](../SCRUTINIZE.md). Read
code only; no database reachable, no tests run. Verdict: **fix-then-ship**. It found every owner
rule implemented and no deadlock or negative-stock path.

| # | Severity | Finding | Repair |
| --- | --- | --- | --- |
| 1 | Medium | No assignment record or TASKS entry (AGENTS.md documentation rule). | `docs/assignments/m45-reversal.md`, TASKS progress line. |
| 2 | Medium-low | Transfer branch of the link trigger had no negative tests; the receipt `warehouse` case was also wrong in quantity, so its warehouse check was unproven. | `test_database_validates_each_transfer_reversal_field` (valid + 5 one-fault cases); warehouse case now −40 at the wrong warehouse. Mutation: removing each check fails exactly its case. |
| 3 | Low | Concurrency tests serialized on the Lot lock; `except IntegrityError` branches never reached. Missing transfer replay/once-only, replay after HOLD, HOLD race, inactive receipt approver. | Cross-Lot same-UUID race test (fails if the except branch is removed); transfer replay/conflict/once-only incl. replay after destination HOLD; HOLD race both orders; inactive approver. |
| 4 | Low | Unapply guard could race a concurrent reversal insert. | `LOCK TABLE inventory_stockreversal IN ACCESS EXCLUSIVE MODE` before the check. |
| 5 | Low | Scope-lock failures surfaced as `ReceiptValidationError` / `TransferQualityValidationError`. | Wrapped as `ReversalValidationError`. |
| 6 | Info | `StockReversal` not in read-only admin; default deferred FKs harmless. | Registered read-only; FKs unchanged. |

Pre-existing, not introduced here: on receipts the registry trigger fires before
`inventory_receipt_transfer_exclusion`, so the registry is not strictly last there.
