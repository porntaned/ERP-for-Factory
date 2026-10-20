# Issue #9 assignment and handoff record

## Assignment

- Repository: `porntaned/ERP-for-Factory`
- Issue: [#9 — Warehouse-scoped role grants foundation](https://github.com/porntaned/ERP-for-Factory/issues/9)
- Branch: `codex/role-warehouse-permissions`
- Base SHA: `b7a9bddd87d258c343d17abbc76e53de9a436dcd`
- Manager and integrator: `/root`
- Scope architect: `/root/m32_scope_architect` — read-only domain and boundary review
- Risk reviewer: `/root/m32_risk_reviewer` — read-only authorization review
- Test writer: `/root/m32_tdd_writer` — PostgreSQL acceptance tests only
- Independent TDD reviewer: `/root/m32_test_reviewer` — read-only test-contract review
- Model implementer: pending assignment — Django Auth, assignment model, migration and policy interface
- Independent implementation reviewer: pending assignment — read-only exact-commit Scrutinize

## Authorized scope

Create the smallest explicit Warehouse-scoped role assignment and evaluation boundary for synthetic
ERP users. Use Django's built-in User identity and one `access_control` assignment model. Do not
claim that later Inventory, Manufacturing or Quality operations are authorized end to end.

## Exclusions

No login or user administration UI, sessions, API authentication, tokens, custom User, Groups as
Warehouse scope, third-party permission package, Organization or Plant grants, inherited roles,
superuser bypass, seeded accounts, reusable passwords, stock behavior, Quality decisions, audit,
Hold/Released state, valuation, merge or deployment.

## Locked schema and policy decisions

- Enable `django.contrib.contenttypes` and `django.contrib.auth`; keep Django's default User.
- `access_control.WarehouseRoleAssignment` contains only `id`, `user`, `warehouse` and `role`.
- Persisted roles are `WAREHOUSE`, `PRODUCTION`, `QUALITY` and `APPROVER`.
- The exact `(user, warehouse, role)` tuple is unique; multiple roles and Warehouses are allowed.
- Assigned Users and Warehouses use protected deletion.
- The policy interface accepts explicit allowed roles and checks the exact Warehouse primary key.
- Anonymous, inactive, unsaved, unassigned, wrong-role and wrong-Warehouse users are denied.
- Empty or unsupported requested roles fail closed. Superuser status creates no implicit bypass.
- Synthetic test users have unusable passwords. No account fixture or credential is published.

## Acceptance for this handoff

1. Tests collect before `access_control` exists and fail only because the locked behavior is absent.
2. PostgreSQL tests cover fields, required and invalid references, roles, uniqueness and deletion.
3. Concurrent exact-duplicate writes prove the database admits one row only.
4. Policy tests cover exact Warehouse scope across sibling Warehouses, Plants and Organizations.
5. Authentication state, role matching, unsupported input and superuser behavior are explicit.
6. A genuine TDD RED is published and independently reviewed before implementation.
7. Implementation later turns the complete suite GREEN without migration drift.
8. An independent reviewer traces the exact implementation commit before an owner-review PR.

## Handoff evidence

Evidence links remain pending until the corresponding commit and GitHub Actions run exist.

The owner decides whether to merge the future pull request. No merge or deployment is authorized.
