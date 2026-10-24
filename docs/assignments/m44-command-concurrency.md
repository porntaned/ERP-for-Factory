# M4.4 — Inventory request and transaction concurrency

Repository `porntaned/ERP-for-Factory`; branch `codex/inventory/concurrent-commands`.
Base: `1e8df0bbf9fb4b19be02fb9145f8ec5e8dff3ecc`. Owner authorized M4.4 on 2026-10-24.
GitHub issue/PR links will be added when created; no issue number is invented.

## Scope and acceptance

Complete request/concurrent-transaction verification for the existing internal Inventory
commands, receipt and same-Plant transfer, plus the underlying immutable ledger. Reuse
already-merged protection rather than introduce a generic movement framework. Add only
missing mixed-command, opposite-direction and waiting-after-rollback tests. Require
targeted PostgreSQL tests, full regressions, recorded SHA and separate source review.

No new request policy, production command/model/migration, dependencies, automatic retry,
HTTP/UI, real data, stock adjustment, reversal, valuation or deployment. M4.5–M4.7 and
future Manufacturing commands remain outside scope. PR #41 and docs closeout PR #46
were verified open and remain separate; this branch starts from main, not either PR.

## Baseline and gap audit

Git origin and clean working tree verified; fetched main at the base above. PR #45 merged;
[main Foundation #137](https://github.com/porntaned/ERP-for-Factory/actions/runs/40068412839)
passed. GitHub had only the separate handoff Issue #40 open at inspection.

| Required behavior | Existing implementation / evidence | M4.4 addition |
| --- | --- | --- |
| UUID required, exact replay returns original; changed payload conflicts | `inventory/services.py`, `inventory/transfers.py`; receipt and request tests | No reimplementation |
| Unique request IDs; failed transactions do not consume keys | unique model fields; existing request/receipt rollback and UUID race tests | Waiting same-key caller proceeds after first rollback, identical or changed reason, for both commands |
| Current active actor and exact WAREHOUSE grants still required on replay | locked authorization before lookup; receipt/atomic/request tests | Retain existing regressions |
| Committed stock only; no negative balance, no half transfer or losing-write orphan | shared Lot serialization, ledger triggers, nested atomic writes; existing ledger/receipt/transfer tests | Receipt versus transfer, both orders and first commit/rollback |
| Opposite transfers conserve stock without lock inversion | persisted scope / ordered parent locks; atomic transfer tests | Both directions started first on separate PostgreSQL sessions |
| Receipt and transfer request namespaces remain independent | separate typed receipt/transfer unique UUID storage; existing command implementations | Mixed-command tests intentionally reuse one UUID across command types |
| Quality and parent identities do not change during writes | existing Quality, authorization, identity/lifetime blocking tests | Preserve Quality history snapshots in mixed and opposite transfers |

Paths above are in [Inventory](../../inventory/) and [inventory tests](../../tests/inventory/).
New [tests](../../tests/inventory/test_command_concurrency.py) use real commands, separate
connections, explicit `pg_blocking_pids` observation and bounded joins/timeouts. A release
by commit or rollback occurs only after the second writer demonstrably waits. No mocks,
SQLite or timing-only race assertions. Opposite-direction commands are ordinary new
transfers, not Reversal transactions referencing an original posting.

## Verification and review

Root implements and self-verifies. Local Windows has no `.env`; no local PostgreSQL
result is claimed. Ruff check/format and `git diff --check` passed. Disposable CI
PostgreSQL 18.6 must verify the new targeted tests followed by the full suite.
Evidence and separate source review are pending; M4.4 acceptance/merge remains pending.
