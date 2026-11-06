# M4.3.3 — Transfer Quality eligibility (owner-selected policy)

> Current status (2026-10-24): owner-merged [PR #35](https://github.com/porntaned/ERP-for-Factory/pull/35); M4.3 accepted through PR #45. See [closeout evidence](../evidence/m43-closeout.md). Pre-merge scope, exclusions and pending statements below are historical.

Repository: `porntaned/ERP-for-Factory`  
Branch: `codex/inventory/transfer-quality-eligibility`  
Base: `6c6c4fb7aec5705f626a3975a53dd5eb9f8578ed`  
[Issue #34](https://github.com/porntaned/ERP-for-Factory/issues/34).
Status: selected policy implemented; PostgreSQL verification passed; ready for owner review; not merged.

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

PostgreSQL results are recorded below. Source and tests changed; no schema, role grant,
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
- Self-review only. No independent agent review is claimed. Verdict: **ship** for this bounded gate: the selected matrix and real serialization
  passed on PostgreSQL. Full posting integration remains in M4.3.4.

## Local verification

Windows PowerShell / `.venv/Scripts/python.exe -m ruff check .`: PASS.
Ruff format applied to the two Python files. No local PostgreSQL test claim: `.env`
is absent. CI must verify the exact pushed SHA on PostgreSQL before owner review.

## PostgreSQL evidence — 2026-10-23

Tested application SHA: `c1f50d2a05f5d6b76a22e74845bbc7ed3796c6c0`.
[Foundation #113 / job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39975578596/job/120489149797)
completed successfully on ubuntu-24.04, PostgreSQL **18.6 (Debian 18.6-1.pgdg12+2)**,
Python/Django/psycopg pinned by the existing workflow. Database connection log confirmed
`vendor=postgresql`. Fresh migration and migration-state checks, Django check and Ruff passed.

| Actual command | Observed result |
| --- | --- |
| `uv run pytest -q tests/inventory/test_transfer_quality.py --tb=short` | **36 passed in 1.54s** |
| `uv run pytest -q --tb=short` | **525 passed in 17.62s** |

The targeted matrix includes 9 default/HOLD/RELEASED combinations, pair-specific history,
15 invalid input variants, stale cached identities, autocommit/isolation rejection and
4 observed PostgreSQL lock-wait cases. Source Quality HOLD committed before the gate
causes rejection; a later HOLD waits for the caller transaction. Destination HOLD is
observed and preserved. No ledger row is written by these checks.

Local Markdown validation: 2 files / 112 local targets PASS; `git diff --check` PASS.
This evidence is self-verification, not independent review. The final documentation-only
commit must also pass CI before the PR is ready to merge. Owner approval to merge has
not been requested or inferred for this work.
