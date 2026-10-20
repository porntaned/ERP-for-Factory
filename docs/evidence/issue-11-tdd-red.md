# Issue #11 — PostgreSQL TDD RED evidence

## Verified commit

- Commit: [`78b2a8a8a00537ba70b9894e7443ddf792d91ee8`](https://github.com/porntaned/ERP-for-Factory/commit/78b2a8a8a00537ba70b9894e7443ddf792d91ee8)
- Branch: `codex/audit-release-hold`
- GitHub Actions: [Foundation #35](https://github.com/porntaned/ERP-for-Factory/actions/runs/39452581694)
- Environment: GitHub Actions with PostgreSQL 18.6

## Commands and results

The workflow ran dependency synchronization, Django configuration checks, a PostgreSQL connection
check, migration drift detection, fresh migrations, Ruff and the complete pytest suite.

- Django configuration: passed
- PostgreSQL connection: passed
- Migration drift and fresh migrations: passed
- Ruff: passed
- Pytest: expected RED — `174 passed, 70 errors in 2.91s`

Every Quality error stopped at the same controlled boundary:
`quality Lot disposition contract is absent; expected RED until Issue #11 is implemented`.
The 174 existing tests remained GREEN, so this RED demonstrates the missing Issue #11 behavior
rather than a regression or an unavailable database.

## Contract covered before implementation

The 70 Quality cases cover Warehouse-scoped state, fail-safe HOLD, exact QUALITY authorization,
same-Organization validation, transition rules, reason and UUID validation, idempotent retry,
stale commands, rollback, protected references, append-only history, direct-write chain integrity,
server timestamp behavior and service/direct-write concurrency on PostgreSQL.

## Review outcome

The first independent review found three test gaps: deferred FK timing, concurrent direct inserts and
database timestamp evidence. Commit `78b2a8a` repaired all three. The exact-commit re-review returned
`ship`; implementation may start from this contract.
