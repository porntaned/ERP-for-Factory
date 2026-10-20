# Issue #1 assignment and handoff record

## Assignment

- Repository: `porntaned/ERP-for-Factory`
- Issue: [#1 — Organization, Plant and Warehouse constraints](https://github.com/porntaned/ERP-for-Factory/issues/1)
- Branch: `feat/warehouse-foundation`
- Base SHA: `0fa90d3d967e5a167ce6a081ca96fe7355eedc43`
- Manager and implementer: `/root`
- Stack analyst: `/root/stack_versions` — read-only version compatibility research
- Test designer: `/root/tdd_red_design` — read-only acceptance and RED-path design

## Authorized scope

Prepare the pinned Python/Django/PostgreSQL test environment, define secret-free development and
test configuration, write the Issue #1 behavior tests and record a genuine PostgreSQL TDD RED.

## Exclusions

No domain models, migrations, stock, quality, accounting, UI, API, authentication, production
features, merge or deployment. The minimal Django settings package exists only to make the RED
test path executable; M2.2 remains incomplete until the three domain models exist.

## Acceptance for this handoff

1. Exact compatible versions are recorded in project metadata and documentation.
2. GitHub Actions can install the locked environment and connect to PostgreSQL 18.6.
3. Secrets are supplied through ignored environment files or synthetic job-only values.
4. Tests encode the Issue #1 hierarchy, scoped uniqueness, code format, parent integrity,
   deletion protection, Thai text and concurrent-write behavior.
5. The targeted RED fails because `facilities.Organization` is not registered, after PostgreSQL
   and Django setup succeed.

Commands, results, the tested commit and the CI run URL are added after the first remote run.
