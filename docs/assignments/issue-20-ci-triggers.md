# Issue #20 — general Foundation CI triggers

- Repository: `porntaned/ERP-for-Factory` only.
- Issue: https://github.com/porntaned/ERP-for-Factory/issues/20
- Branch: `codex/ci/general-triggers` (nested, absent from the old whitelist).
- Base main: `95d612bc41b4bda184598ba30f7072c4896f976d`, owner-authorized PR #19 merge.
- Recovery: original branch `codex/fix-quality-event-identity`, HEAD
  `59aca552f0ac5a60d3386804b3fe68b9c17f4d21`, clean working tree. Fetched origin/main
  confirms merged Finding 3. Browser issue inventory showed no open issue before #20.
- Scope: audit Finding 4 only, plus reconcile PA.5/Finding 3 with its actual merge.
- Allowed files: Foundation trigger block, issue assignment/evidence/review, TASKS and
  prior Finding 3 merge evidence. No application/schema/test-body changes.
- Trigger contract: pushes to `main`, `codex/**`, `feat/**`; retain pull requests targeting
  `main`. Keep the entire job, permissions, action pins, runtime and PostgreSQL tests intact.
- Manager/implementer/verifier: `/root`; own CI inspection is self-verification.
- Independent read-only reviewer will inspect the exact change and captured evidence
  under MULTI_AGENT/SCRUTINIZE; roles are recorded only as actually performed.
- Acceptance: historical names removed; actual push runs on nested codex and feat refs;
  actual PR-to-main run; PostgreSQL/checks/migrations/Ruff remain passing; main filter
  statically verified against official GitHub semantics; exact refs/SHAs/runs recorded.
- Dependencies: existing GitHub Actions access through the prepared browser and unchanged
  PostgreSQL 18.6 CI service. No local PostgreSQL runtime is claimed.
- Probe: create `feat/ci-trigger-probe/issue-20` at the same implementation commit,
  without changing the workflow or opening another PR. Retain the evidence ref for review.
- Main-push limit: no synthetic push to protected main and no automatic merge. Actual
  post-merge main execution is an owner check after this PR merges, not pre-merge evidence.
- Exclusions: README/Finding 5, product features, migrations, new dependencies, concurrency,
  permissions redesign, real data, secrets, stock/valuation, force-push, merge and deployment.
- Repair limit: two cycles for one failed finding; a third recurrence stops for owner review.
- Stop: separate owner-review PR; do not begin Finding 5.

## Verification plan

Inspect old/new event selection rather than inventing a failing business test for a
declarative trigger change. Use real GitHub push/PR events and the unchanged PostgreSQL
suite. No new YAML package, glob-matching test double or test-count claim is required.
Before PR, apply Scrutinize and label self-verification versus independent inspection.
Only check progress after linked evidence exists.

Official reference: [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
Its branch filters match ref names, `**` supports nested branch paths, and PR filters
select target branches. Confirmed through the prepared browser on 2026-10-22.

## Implementation handoff

Implementation `56a0d80f05250751b3e5025b1c28ec5f6137d60c` changes only the push filter
and the allowed documentation. Actual new nested codex/feat push runs both succeeded,
with 281 PostgreSQL tests each. [Commands and captured evidence](../evidence/issue-20-ci-triggers.md).
Independent read-only reviewer `/root/issue20_independent_review` returned
[ship for opening the owner-review PR](../reviews/issue-20-ci-triggers-independent-review.md).
No repair cycle was needed. PR event verification is the next verifier action;
main post-merge observation and acceptance remain with the owner.

## Final delivery

[PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21) is open for owner review.
Actual PR opened event succeeded with 281 tests; exact head/checkout SHA and run are
linked in the evidence report. Independent reviewer inspected this additional capture
and returned `ship` for handoff. Earlier next-action wording is historical.
The final bookkeeping commit does not change the tested workflow or application.
Manager checks its latest PR checks before handoff. Issue #20 and overall PA.6 remain
pending owner acceptance/main-push observation. Work stops here; no merge, deployment
or Finding 5.
