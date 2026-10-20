# Issue #1 assignment and handoff record

## Assignment

- Repository: `porntaned/ERP-for-Factory`
- Issue: [#1 — Organization, Plant and Warehouse constraints](https://github.com/porntaned/ERP-for-Factory/issues/1)
- Branch: `feat/warehouse-foundation`
- Base SHA: `0fa90d3d967e5a167ce6a081ca96fe7355eedc43`
- Manager and integrator: `/root`
- Stack analyst: `/root/stack_versions` — read-only version compatibility research
- Test designer: `/root/tdd_red_design` — read-only acceptance and RED-path design
- Model implementer: `/root/m2_models_implementer` — facilities models and initial migration
- Schema reviewer: `/root/m2_schema_reviewer` — read-only constraint design review
- Independent reviewer: `/root/independent_scrutinize` — read-only end-to-end Scrutinize

## Authorized scope

Prepare the pinned Python/Django/PostgreSQL test environment, define secret-free development and
test configuration, prove a genuine RED, then implement and independently review only the
Organization → Plant → Warehouse schema required by Issue #1.

## Exclusions

No stock, quality, accounting, UI, API, authentication, production features, merge or deployment.
The issue is limited to three domain models, their first migration and database-level behavior.

## Acceptance for this handoff

1. Exact compatible versions are recorded in project metadata and documentation.
2. GitHub Actions can install the locked environment and connect to PostgreSQL 18.6.
3. Secrets are supplied through ignored environment files or synthetic job-only values.
4. Tests encode the Issue #1 hierarchy, scoped uniqueness, code format, parent integrity,
   deletion protection, Thai text and concurrent-write behavior.
5. The targeted RED fails because `facilities.Organization` is not registered, after PostgreSQL
   and Django setup succeed.
6. The implementation turns the complete suite GREEN on PostgreSQL without migration drift.
7. An independent read-only reviewer traces the implemented path and records a verdict.

## Handoff evidence

- RED commit: [`31ba6be9cf94f50f28267734f7040a4592db3545`](https://github.com/porntaned/ERP-for-Factory/commit/31ba6be9cf94f50f28267734f7040a4592db3545)
- RED run: [Foundation #1](https://github.com/porntaned/ERP-for-Factory/actions/runs/39355731564)
- RED record: [PostgreSQL TDD RED evidence](../evidence/issue-1-tdd-red.md)
- GREEN commit: [`8fdb446669c47f892774c2fba2c2093ba4d1c1e8`](https://github.com/porntaned/ERP-for-Factory/commit/8fdb446669c47f892774c2fba2c2093ba4d1c1e8)
- GREEN run: [Foundation #4](https://github.com/porntaned/ERP-for-Factory/actions/runs/39369435238)
- GREEN record: [PostgreSQL GREEN evidence](../evidence/issue-1-green.md)
- Independent review: [Issue #1 implementation review](../reviews/issue-1-foundation-independent-review.md)
- Owner-review PR: [#3 — Add Organization, Plant, and Warehouse foundation](https://github.com/porntaned/ERP-for-Factory/pull/3)
- Governance merge: [`ec79831bf0cd3b58ec8f204cdb9b74c3fdf3f0a7`](https://github.com/porntaned/ERP-for-Factory/commit/ec79831bf0cd3b58ec8f204cdb9b74c3fdf3f0a7)
- Foundation merge: [`1f7acc61d446e581d89588b96b80f7d4f25609f8`](https://github.com/porntaned/ERP-for-Factory/commit/1f7acc61d446e581d89588b96b80f7d4f25609f8)

The RED run installed the locked stack, passed Django configuration, connected to PostgreSQL 18.6
and failed because `facilities.Organization` did not exist. The GREEN run at the repaired commit
repeated that environment path, found no migration drift, applied the fresh migration, passed Ruff
and completed 51 tests. Local checks passed except that database behavior was collected rather
than executed because no local PostgreSQL server was available.

The independent reviewer first found a direct NOT NULL regression-test gap. The integrator added
eight database-boundary cases, and the reviewer re-traced the exact repaired commit with no
remaining blocker, major or minor finding. The owner merged Governance PR #2, retargeted PR #3 to
`main`, and verified that the comparison still contained only the six Issue #1 commits and 25
Issue #1 files. PR #3 then merged as `1f7acc61d446e581d89588b96b80f7d4f25609f8`, closing Issue #1
as completed. No deployment was performed.
