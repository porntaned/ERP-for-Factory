# M4.3.7 — transfer readiness

Repository: `porntaned/ERP-for-Factory`; branch: `codex/inventory/transfer-readiness`.
Owner authorized M4.3.7 on 2026-10-24. Base: `e8ad707b86f7c613c3db291fd6dcabd3f491a569`.
Issue creation is pending explicit approval after automatic approval review rejected
creating a new GitHub issue. No issue number is invented.

## Scope and acceptance

Verify M4.3.1–M4.3.6 through the existing internal command, adding only missing
receipt/Quality/transfer integration coverage. Require real PostgreSQL targeted and
full regression evidence at an exact SHA, followed by separate independent Scrutinize
review. No policy change, new dependency, UI/API, M4.4 completion, reversal, real data,
automatic merge or deployment. PR #41 remains separate and is not merged here.

The smaller solution is tests and evidence only: existing command/storage behavior
already has detailed invalid-input, history, migration, rollback and concurrency tests.

## Coverage trace

| Claim | Real path | Verification source |
| --- | --- | --- |
| Persisted same-Plant identity, positive exact Decimal, preserved reason | `transfer_stock` -> `_validate_payload` / `lock_transfer_scope` | `test_atomic_transfer.py`, `test_transfer_quality.py` |
| Active actor and both current WAREHOUSE grants; no role bypass | `transfer_stock` -> locked actor/grants | `test_atomic_transfer.py`, `test_transfer_requests.py` |
| Source RELEASED; destination disposition unchanged | `transfer_stock` -> `get_lot_disposition` | `test_atomic_transfer.py`, `test_transfer_quality.py` |
| Conserved stock, insufficient-stock rejection and all-or-nothing writes | command transaction / ledger triggers | `test_atomic_transfer.py` |
| Immutable linked debit/credit and database identity/time | StockTransfer / migrations 0002–0006 | `test_transfer_history.py`, `test_transfer_requests.py` |
| Exact replay, changed-payload conflict, current authorization on retry | `_existing_transfer` after authorization | `test_transfer_requests.py` |
| Actual lock waits, overspend protection, Quality/grant serialization, UUID race losing-write rollback | command / real PostgreSQL sessions | `test_atomic_transfer.py`, `test_transfer_requests.py`, shared `blocked_action` helper |
| Receipt default HOLD -> rejected transfer -> Quality release -> transfer -> linked history -> replay/conflict -> denied replay after grant removal | `receive_stock`, `transition_lot_disposition`, `transfer_stock`, balance queries | new `test_transfer_workflow.py` (default HOLD / RELEASED destination) |

Test paths are relative to [tests/inventory](../../tests/inventory/).
New workflow uses only real commands and synthetic records, without pre-seeding ledger
or Quality events. It checks exact fractional quantities, Unicode reasons, receipt
identity separation, unchanged histories on rejection/retry, and disposition events.
It is an internal-command integration test, not an HTTP/browser workflow or M4.7 demo.

## Baseline evidence and environment

Verified Git origin URL, clean working tree, PR #43 merged and origin/main at the base.
[Main Foundation #132](https://github.com/porntaned/ERP-for-Factory/actions/runs/40067226064)
passed after PR #43. PR #39 and #43 are merged; checklist cleanup must cite those facts.

Local Windows PowerShell has no `.env`, so no local PostgreSQL result is claimed.
Local Ruff was run directly from `.venv/Scripts/ruff.exe`; the `uv run` launcher
encountered a sandbox cache permission failure, which is an environment failure,
not a RED business test. PostgreSQL verification uses disposable CI PostgreSQL 18.6.

## Verification and review status

Implementation: root. Self-verification and self-review must be labelled separately
from the independent reviewer. Targeted/full CI and independent review are pending;
M4.3.7 and overall M4.3 are not yet accepted. Owner merge remains a separate decision.
