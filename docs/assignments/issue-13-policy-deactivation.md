# Issue #13 — persisted deactivation

- Repository: `porntaned/ERP-for-Factory` only.
- Issue: https://github.com/porntaned/ERP-for-Factory/issues/13
- Branch: `codex/fix-policy-deactivation`.
- Base: `9b1d182eb6867b70f076e95a63dc03f1814f00ec`.
- Scope: audit Finding 1 only; deny retained active User instances after persisted deactivation in both Warehouse policies, including lazy QuerySet evaluation.
- Exclusions: Finding 2 (unsaved User with supplied PK), event IDs, general CI redesign, README, migrations, Inventory, merge and deployment.
- Manager/verifier: `/root`; verification performed by manager is self-verification.
- Test author: `/root/fix_deactivation_implementer`; its earlier turn stopped on usage limit after leaving three uncommitted regressions. Manager inspected and resumed those tests.
- Implementation: manager after PostgreSQL RED. Independent reviewer assigned after implementation.
- Allowed files: policies, targeted access-control tests, branch-specific CI entry, issue evidence/review and checklist.
- Acceptance: both policies deny persisted inactive users; pre-created unevaluated queries observe deactivation; existing active grants/isolation pass; PostgreSQL regression, Django/migration checks and Ruff pass; independent Scrutinize and PR recorded.
- Stop: deliver Finding 1 for owner review; do not start Finding 2.

## Existing RED context

[Audit run #47](https://github.com/porntaned/ERP-for-Factory/actions/runs/39540468833) demonstrated two deactivation failures among five audit reproductions. The separate audit branch and its other failing tests remain intact. This branch starts from main and adds only Finding 1 regressions; a GREEN suite here does not resolve other audit findings.

## Progress

- [x] Issue and scope confirmed; retained test draft inspected.
- [x] New scoped PostgreSQL RED recorded — [evidence](../evidence/issue-13-policy-deactivation.md#red).
- [x] Minimal fix and PostgreSQL GREEN recorded — [evidence](../evidence/issue-13-policy-deactivation.md#green).
- [x] Independent Scrutinize recorded — reviewer `/root/issue13_independent_review`, [report](../reviews/issue-13-policy-deactivation-independent-review.md), verdict `ship` at `abe63e154de62e7d37f3ff4c47252f6a88c07587`.
- [ ] Owner-review PR opened.
