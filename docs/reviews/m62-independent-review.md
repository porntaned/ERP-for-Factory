# Review — PR #104 (Issue #103, M6.2: REJECTED Lot unusable at every warehouse)

**Type: independent review by a separate session** (Claude Code session `session_01MVmjhbsKYvC1RZ5mHmggzs`,
created by the Manager session as a separate session; read-only, code-reading only, ran no tests).
It is not an owner review. Date 2026-11-06. Reviewed head `ea2c26f` (branch
`claude/keen-feynman-jkijlw`). Spec: `docs/assignments/m62-hold-release-enforcement.md`.

The Reviewer was given only the PR number, the Issue number and the spec path. The section
"Report" is the Reviewer's message as received (copied by the Manager without edits). The section
"Manager disposition" is the Manager's own and is not part of the review.

## Report

Evidence status: CI on PostgreSQL 18.6 was still in_progress when I looked (run 42260613418), and the PR had no CI comment. The only results so far are the Implementer's local runs on PG16 (1067 passed at fe8aa71). Those are development checks and self-verification. Do not treat the slice as verified until the CI comment exists and matches ea2c26f.

INTENT: A Lot REJECTED at any warehouse must be unusable everywhere except SCRAP and the reversal of a receipt or an OUTPUT. The rule is enforced in the commands and by a deferred PostgreSQL trigger. The change should exist, and I found no smaller solution. The trigger is the only protection against a direct INSERT, and the command checks give clean errors.

TRACED (no defect found):
- inventory/transfers.py:_post_transfer. lock_transfer_scope takes the Lot lock first, then the replay check, then the RELEASED gate, then require_lot_not_rejected, then the balance check and writes. Covers transfer, issue and return.
- inventory/services.py:receive_stock. The gate sits after the replay and key-conflict checks and before the write.
- inventory/production.py:post_production_posting. The gate runs for CONSUME and OUTPUT, not SCRAP. The Lot is locked by _lock_receipt_parents.
- inventory/production.py:reverse_production_posting. Refused for CONSUME and SCRAP originals, allowed for OUTPUT.
- inventory/reversals.py:reverse_transfer. The gate runs after the RELEASED gate and after the replay check. reverse_receipt is unchanged.
- Locking and race. Quality's record_inspection and transition_lot_disposition both do Lot select_for_update (quality/services.py:158 and :305). The commands lock the Lot too. So a rejection and a movement of the same Lot serialize under READ COMMITTED, and the post-lock read of events is fresh. The trigger covers raw INSERTs.
- inventory/migrations/0015: column and table names match models.py (StockReversal.debit_entry and receipt, ProductionPosting.ledger_entry and kind, ProductionPostingReversal.posting and ledger_entry). The exemption requires a debit linked as SCRAP, a receipt reversal or an OUTPUT reversal. "Latest event per warehouse" matches get_lot_disposition. The migration is reversible and uses SET CONSTRAINTS ALL IMMEDIATE before and after, as 0006 did.
- manufacturing/services.py. MaterialLotRejectedError subclasses MaterialQualityError and is mapped in the issue/return, consume/scrap/output and reverse_order_posting paths. In demo/production_views.MESSAGES the subclass entry comes before its parent, so it matches first.
- Docs. TASKS.md and README are untouched, which matches the spec. DEVELOPMENT.md and the m61 note are updated.

FINDINGS (by severity):

1. MEDIUM (process). Missing review record: docs/reviews/m62-independent-review.md. The spec requires it in the same PR, and I am read-only. After this report, someone must write that file with its type on the first lines ("independent review by a separate session"). The spec's Status line ("review so far: none", "Reviewer ... not started", "CI has not run") must then be updated. Smallest change: add the file and update the Status and Roles lines.

2. MEDIUM (evidence). There is no CI evidence on PG18.6 yet, and all test claims rest on PG16 local runs. The trigger and migration are PostgreSQL-specific claims (AGENTS.md: verify on PostgreSQL, CI is the record). Smallest change: wait for CI to finish and cite the CI comment (SHA ea2c26f, server 18.6, counts) in the spec's evidence section. Keep the "development check" label on the PG16 numbers.

3. LOW (UX/contract, Implementer ruling 1). A Lot REJECTED at the source of a transfer or issue, or at the leaving warehouse of a reversal, still raises TransferQualityError or ReversalQualityError, not LotRejectedError. On the production screen that shows "Lot ต้องเป็น RELEASED ที่คลังต้นทาง", which is accurate but less specific than the new REJECTED message. The behaviour is refused in all three positions either way, and existing tests pin the old errors, so this is acceptable. It is flagged because the spec's acceptance row says "refused", and the Implementer's note says the test expectation was changed to match ruling 1. The owner should confirm. Smallest change if not wanted: in _post_transfer and reverse_transfer, call the new gate before the RELEASED gate and update the two old tests.

4. LOW (test harness). tests/quality/helpers.settle() and the three small edits to existing tests exist because the deferred trigger checks at teardown against the current disposition, not the disposition at insert time. In production, a transaction that inserts a legitimate ledger entry and then rejects the same Lot before commit would fail. No such production path exists today. The seed and demo commands pass in the Implementer's run, but I did not verify that. Smallest change: none needed. Record in the closeout that "reject after a movement in the same transaction" is unsupported by design, and that M6.3/M6.4 must not combine the two in one transaction.

5. LOW (scope hygiene). The trigger's RAISE message has no Lot id or code. Debugging a failed commit then needs a lookup, but Django surfaces it as IntegrityError and the commands give friendly errors first. Optional: add NEW.lot_id to the message.

NOT VERIFIED: I did not run the suite or the two-connection race tests, and I did not check the migration unapply/reapply or the Thai screen messages on a live database. I rely on the code reading above and on the Implementer's reported results.

SIMPLER ALTERNATIVE CONSIDERED: command checks only, without the trigger. Rejected: the repo's pattern (M6.1 migrations 0006/0007) is to back every Quality rule in PostgreSQL, and direct INSERTs would otherwise bypass the rule.

VERDICT: fix-then-ship. The biggest reason is that CI evidence is pending and the required review record (finding 1) is not in the PR. No code defect found. Ship once CI on PG18.6 is green at the final SHA, the review file is added, and the owner confirms ruling 1.

## Manager disposition (Manager session, repair round 1 of 2)

| # | Disposition |
|---|---|
| 1 | Fixed: this file added; spec Status and Roles updated. |
| 2 | Closed: CI on PostgreSQL 18.6 passed (1067) on `ea2c26f` and `01e235a`, cited in the spec; PG16 numbers keep the "development check" label. |
| 3 | **Not changed; owner to confirm.** Spec says the existing per-warehouse gates "stay as they are", and two existing tests pin them. |
| 4 | Not changed (no production path). Recorded in the spec as unsupported by design for M6.3/M6.4. |
| 5 | Not changed: optional, and the commands give the friendly error first. Left as an observation to avoid touching the migration after review. |

The fixes in this round are documentation only. They were not re-reviewed by the Reviewer.
