# Issue #11 assignment and handoff record

## Assignment

- Repository: `porntaned/ERP-for-Factory`
- Issue: [#11 — Warehouse-scoped Lot disposition audit foundation](https://github.com/porntaned/ERP-for-Factory/issues/11)
- Branch: `codex/audit-release-hold`
- Base SHA: `6f6e06b`
- Manager and integrator: `/root`
- Scope architect: `/root/m33_scope_architect` — read-only boundary and simpler-alternative review
- Risk reviewer: `/root/m33_risk_reviewer` — read-only authorization, ownership and concurrency review
- Test-contract reviewer and test writer: `/root/m33_test_contract`
- Independent TDD reviewer: `/root/m33_red_independent_review` — read-only exact-commit review
- Implementer: `/root/m33_implementer` — production implementation and request-conflict repair
- GREEN evidence verifier: `/root` — project self-verification from exact-commit GitHub Actions logs
- Independent implementation reviewer: `/root/m335_independent_review` — read-only review/re-review
- Review repair implementer: `/root/m335_repair` — production and regression-test fixes

## Authorized scope

Create a typed append-only Quality decision history for the exact `(lot, warehouse)` pair. Missing
history is fail-safe `HOLD`. An active User with an explicit `QUALITY` grant for that exact Warehouse
may record `HOLD` to `RELEASED` or `RELEASED` to `HOLD` with a nonblank reason and idempotency key.
The Lot Item and Warehouse must belong to the same Organization.

## Exclusions

No inspection records, sampling, defect results, stock quantities, stock ledger, receiving,
transfers, movement blocking, manufacturing, valuation, generic audit framework, UI, API, seeded
accounts, real factory data, merge or deployment. This issue does not claim that Inventory already
blocks movement of a held Lot.

## Locked decisions

- Disposition is Warehouse-scoped; no global status is added to `inventory.Lot`.
- Quality owns the decision and typed history. Inventory will consume the query interface later.
- Only `HOLD` and `RELEASED` are valid; absence means `HOLD` and writes no synthetic event.
- No-op transitions and stale expected state fail without adding history.
- Exact-Warehouse `QUALITY` authorization is required; superuser status is not a bypass.
- Events retain protected Lot, Warehouse and actor references, server time, nonblank reason and a
  unique UUID request key.
- State recheck and append occur in one PostgreSQL transaction. Exact retries converge on one event;
  reused keys with different payload fail.
- PostgreSQL protects valid state values, chain integrity and append-only history against direct
  writes, updates and deletes.

## Acceptance for this handoff

1. Tests collect before the Quality disposition contract exists and fail only for that absence.
2. PostgreSQL tests cover exact scope, authorization, same-Organization rules and protected refs.
3. Tests cover invalid/no-op/stale transitions, reason validation and atomic rollback.
4. Retry and concurrency tests prove one authoritative transition and an unbroken event chain.
5. Direct PostgreSQL writes cannot forge, update or delete recorded history.
6. A genuine TDD RED is published and independently reviewed before implementation.
7. Implementation later turns the complete suite GREEN without migration drift.
8. An independent reviewer traces the exact implementation commit before an owner-review PR.

## Handoff evidence

- Scope review: [Independent M3.3 scope review](../reviews/issue-11-scope-independent-review.md)
- TDD RED: [PostgreSQL RED evidence](../evidence/issue-11-tdd-red.md)
- Independent TDD review: [exact-commit review](../reviews/issue-11-tdd-red-independent-review.md)
- M3.3.3 implementation: [implementation handoff](#m333-implementation-handoff)
- GREEN implementation: [M3.3.4 evidence and repair verification](../evidence/issue-11-green.md), latest [Foundation #42](https://github.com/porntaned/ERP-for-Factory/actions/runs/39528381765) at `44b466fdd4e9d0134564c77aef7a316c1a2b8b7e`
- Independent implementation review: [review and repair record](../reviews/issue-11-lot-disposition-independent-review.md), final verdict `ship` at `44b466f`
- Owner-review pull request: pending

The owner decides whether to merge the future pull request. No deployment is authorized.

## M3.3.3 implementation handoff

Recorded on 2026-10-21 by `/root` from the existing implementation and GitHub evidence.
At that handoff, the owner had authorized completing M3.3.3 only. The subsequent M3.3.4
authorization and completion are recorded in the remaining-work status below.

- Implementer: `/root/m33_implementer`; manager and handoff recorder: `/root`.
- Initial implementation: [`b1bc0405f26052d701181fc174e03ae08edb3170`](https://github.com/porntaned/ERP-for-Factory/commit/b1bc0405f26052d701181fc174e03ae08edb3170).
- Latest production commit: [`825b34fea7ad16605210ef4760a41627f0965c06`](https://github.com/porntaned/ERP-for-Factory/commit/825b34fea7ad16605210ef4760a41627f0965c06).
- Files: [Quality model](../../quality/models.py), [query/transition services](../../quality/services.py),
  [initial migration](../../quality/migrations/0001_initial.py), [app configuration](../../quality/apps.py),
  package initialization files and [Django settings](../../config/settings.py).

### Delivered implementation

- Typed `LotDispositionEvent` for an exact Lot/Warehouse pair, with protected references, UUID
  request key, from/to disposition, reason and database-generated time.
- `get_lot_disposition` returns the latest decision or `HOLD` when history is absent.
- `transition_lot_disposition` uses the existing exact-Warehouse QUALITY policy, validates the
  Organization boundary, locks the Lot, resolves retries, checks expected state and appends an event.
- Migration creates the model and constraints, plus PostgreSQL insert/immutability triggers.
- The request-conflict repair resolves an existing request key before validating a new transition.

### Existing verification and handoff checks

At production commit `825b34fea7ad16605210ef4760a41627f0965c06`,
[Foundation #38](https://github.com/porntaned/ERP-for-Factory/actions/runs/39454155496)
completed successfully. Its PostgreSQL connection check, `uv run python manage.py check`,
`uv run python manage.py makemigrations --check --dry-run`,
`uv run python manage.py migrate --noinput`, `uv run ruff check .` and
`uv run pytest -q --tb=short` steps all passed. This links existing CI evidence for the delivered
implementation. The later M3.3.4 report uses Run #39 at the newer tested commit linked above.

On 2026-10-21, `/root` confirmed the local and GitHub branch heads both matched `825b34f`, with a
clean working tree before documentation changes. Local self-verification in the Windows `.venv`
with synthetic environment values ran:

```powershell
.\.venv\Scripts\ruff.exe check quality config/settings.py
.\.venv\Scripts\python.exe manage.py check
```

Results: `All checks passed!` and `System check identified no issues (0 silenced).`
These local checks did not execute PostgreSQL tests and are not independent review.

### Remaining work

M3.3.3 is delivered on the feature branch. It does not mark the whole Issue #11 complete, approve
merge, or establish an independent implementation verdict. M3.3.4 was subsequently authorized and
completed with the [GREEN evidence report](../evidence/issue-11-green.md): Run #39 verified all 244
tests on PostgreSQL at `7ce4ef84570628234d4097e0b95643bbf38880db`. M3.3.5 was then authorized:
independent review found three integrity defects, the repair agent fixed them, and exact-commit
re-review returned `ship` at `44b466f` with 261 passing PostgreSQL tests. The owner-review PR is pending.
Stock movement enforcement, inspections and UI remain outside this issue.
