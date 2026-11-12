# M4.4.2 — stale branch port, transfer key required, registry test gaps

Repository `porntaned/ERP-for-Factory`; branch `codex/inventory/m44-hardening`; base `main`
`32ca3d2e93ea5f9dd879c8a28b9c85f1d26d9db8`. [Issue #53](https://github.com/porntaned/ERP-for-Factory/issues/53).
Owner approved on 2026-11-04. No merge or deployment authorized by this work.

## Scope delivered

- **Stale branch** `codex/inventory/concurrent-commands` (fa2f24d, 3530bb6; never a PR, based
  before #49/#51): ported opposing transfers (A→B vs B→A) and same-UUID rollback waiter into
  `tests/inventory/test_command_concurrency.py`; rewrote its mixed receipt/transfer test with
  distinct keys (it reused one UUID across commands, which M4.4.1 rejects). Its doc
  `m44-command-concurrency.md` was not ported because it contradicts the registry decision.
  The branch itself was not deleted. (Historical: the owner archived it as tag
  `archive/codex-inventory-concurrent-commands` (`3530bb6`) and deleted it on 2026-11-12.)
- **Transfer key required:** inventory/0008 `CHECK (request_id IS NOT NULL) NOT VALID` on new
  rows; legacy NULL rows untouched and unregistered. Direct inserts in
  `test_transfer_history.py` now pass a key; their assertions are unchanged.
- **Registry tests:** Quality key reused by receipt; raw disposition insert; cross-command
  race in 4 orderings on a second Lot/actor; quality/0004 abort; legacy NULL upgrade; 0008
  reverse/reapply.
- **Lock order:** quality/0005 makes the registry trigger fire after the Lot-locking
  validation trigger.
- **CI:** targeted steps for registry, registry migration and concurrency suites.

## RED / GREEN

Only `test_new_transfer_without_request_id_is_rejected_by_postgresql` was RED before the fix
(`DID NOT RAISE IntegrityError`). The ported and added registry tests passed immediately:
they add coverage for behavior that already worked, not fixes.

## Review

Independent review and repairs: [m44-registry-independent-review.md](../reviews/m44-registry-independent-review.md).

## M4.4.1 retroactive record (Issue #50, PR #51)

PR #51 had no assignment record. Summary: owner chose a shared registry on 2026-10-30; RED
first (6 registry tests failed with `DID NOT RAISE`), then GREEN; local full suite 653 passed;
owner confirmed the three assumptions and merged at `7d2ed62` on 2026-11-04; main CI #151
succeeded (step conclusions only). Retroactive independent review: see the review file above.

## Closeout (2026-11-04)

Owner approved merge; [PR #56](https://github.com/porntaned/ERP-for-Factory/pull/56) merged at `5a91d0026f7787f78df45cc079d23f20b428874c`, main CI #164 success; Issue #53 closed. Later merges #55 (`a21208d`, CI #165) and #57 (`45df3cc`, [CI #166](https://github.com/porntaned/ERP-for-Factory/actions/runs/41791823342)) also passed. CI step conclusions only; no test counts read from logs.
