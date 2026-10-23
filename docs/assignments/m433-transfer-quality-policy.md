# M4.3.3 — Transfer Quality eligibility (owner-selected policy)

Repository: `porntaned/ERP-for-Factory`  
Branch: `codex/inventory/transfer-quality-eligibility`  
Base: `6c6c4fb7aec5705f626a3975a53dd5eb9f8578ed`  
[Issue #34](https://github.com/porntaned/ERP-for-Factory/issues/34).
Status: selected policy implemented; PostgreSQL verification pending; not merged.

## Verified baseline

- Clean Git working tree before starting; origin/main fetched at the base above.
- GitHub open issues: 0 at inspection; no existing transfer Quality issue to duplicate.
- [Main Foundation #112](https://github.com/porntaned/ERP-for-Factory/actions/runs/39973076788)
  completed successfully for the base. This is baseline evidence, not transfer evidence.
- [M4.3.1 contract](issue-32-transfer-definition.md) is delivered in PR #33.
- [Quality models](../../quality/models.py) define HOLD and RELEASED only.
- [Quality services](../../quality/services.py) resolve latest event by descending ID for
  each Lot–Warehouse pair; no event means HOLD. Transitions lock the Lot and require
  an active QUALITY grant for the affected Warehouse.
- [Inventory services](../../inventory/services.py) currently implement balances and
  receipts only. Receipt preserves Quality disposition; this does not establish transfer policy.

## Owner decision — 2026-10-23

Owner explicitly selected: source must be RELEASED; destination accepts HOLD/default
HOLD or RELEASED and retains its own disposition. No automatic Quality transitions.

| Source | Destination | Quality gate result |
| --- | --- | --- |
| HOLD/default HOLD | HOLD/default HOLD | Reject |
| HOLD/default HOLD | RELEASED | Reject |
| RELEASED | HOLD/default HOLD | Allow; destination stays HOLD |
| RELEASED | RELEASED | Allow; destination stays RELEASED |

Inventory does not copy source release or append a Quality event. A later transfer
back out of a HOLD destination must fail until Quality releases it. No new state is added.

## Bounded implementation and acceptance plan

Implement only the Inventory-side Quality eligibility boundary
and meaningful PostgreSQL tests. Keep Quality as the owner of dispositions.
M4.3.2 grants, M4.3.4 ledger posting, M4.3.5 transfer history and M4.3.6 request handling
remain separate. Do not add a public stock transfer command as part of this slice.

The eligibility component must not claim to authorize a movement or reserve stock.
Its check must be repeated inside the eventual posting transaction while holding
compatible Lot locks, so a concurrent Quality HOLD cannot slip between check and write.
A standalone successful check is not proof that the future transfer posting is protected.

Planned checks:

- Every source/destination disposition combination, including no-event default HOLD.
- Latest-event ordering; history for another Lot or Warehouse must not affect the pair.
- Both dispositions and Quality history unchanged on success or rejection.
- Invalid/missing/unsaved identities rejected; persisted identities govern eligibility.
- Transaction/locking contract and a concurrent Quality transition on PostgreSQL.
- Existing Quality and Inventory regressions after targeted tests pass.

No PostgreSQL result is recorded yet. Source and tests changed; no schema, role grant,
UI or stock write was added. No merge/deployment is authorized by this request.

## Review ownership

Root prepared this decision draft and traced the linked code. This is self-review;
no independent agent review has been performed or claimed for this slice.

## Implemented boundary and self-Scrutinize

- [Gate](../../inventory/transfer_policy.py): `require_transfer_quality` requires an
  existing caller atomic transaction and PostgreSQL READ COMMITTED. It locks the Lot
  FOR UPDATE, then Item/Warehouses/Plant FOR SHARE in the existing posting order;
  Warehouses are sorted by ID. Parent reads use persisted identities, not caller caches.
- Fresh pair dispositions are read through Quality's existing interface. Source HOLD
  rejects; destination disposition is returned without changing history or balances.
- Locks remain held until the caller's outer transaction ends. The future posting
  service MUST call the gate inside the same transaction as both ledger writes.
  There is no complete transfer command or authorization check in this slice.
- [Tests](../../tests/inventory/test_transfer_quality.py) exercise the policy matrix,
  identity/default/latest-event rules, transaction isolation and both directions of
  serialization with actual Quality transitions. Existing lock-wait helper observes
  `pg_blocking_pids`, rather than assuming a race from a delay.
- CI gains one targeted step, followed by the existing full ERP suite.
- Smaller alternative considered: a Boolean snapshot check would allow Quality state
  to change between checking and posting. Caller-owned locks are needed instead.
- Self-review only. No independent agent review is claimed. Pending PostgreSQL results
  prevent a ship verdict until verified; full posting integration remains in M4.3.4.

## Local verification

Windows PowerShell / `.venv/Scripts/python.exe -m ruff check .`: PASS.
Ruff format applied to the two Python files. No local PostgreSQL test claim: `.env`
is absent. CI must verify the exact pushed SHA on PostgreSQL before owner review.
