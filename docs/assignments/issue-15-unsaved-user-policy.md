# Issue #15 — unsaved supplied-PK User policy boundary

- Repository: `porntaned/ERP-for-Factory` only.
- Issue: https://github.com/porntaned/ERP-for-Factory/issues/15
- Branch: `codex/fix-unsaved-user-policy`.
- Base main: `eba63622495c6b065ad0abcd8e652676f9189d20` (merged PR #14).
- Recovery: original branch `codex/fix-policy-deactivation`, HEAD
  `cd4a373970e68c7be7aae539cfa7ee25640b487d`, clean working tree. Fetch and GitHub
  independently confirmed main, PR #14 merged and Issue #13 completed. No open issues/PRs
  existed before creating Issue #15. Finding 1 is already complete and will not be repeated.
- Scope: audit Finding 2 only; reject never-saved User instances (including manually
  supplied PK collisions) through both shared Warehouse policies.
- Acceptance: deny unsaved colliding/nonmatching/absent PK users; allow active saved/loaded
  users with matching grants; preserve persisted-active checks, role/warehouse isolation
  and distinct query results. Targeted/full PostgreSQL tests and existing checks pass.
- Allowed files: shared policy helper, focused access-control tests, exact branch CI entry
  and targeted step, assignment/evidence/review and checklist reconciliation.
- Exclusions: Finding 3/event IDs, general CI triggers, README, schema/migrations,
  dependencies, Inventory, merge and deployment.
- Dependencies: PR #14 persisted-active filters; existing PostgreSQL CI environment.
- Manager/implementer/verifier: `/root`; own checks are self-verification.
- Reviewer: a separate read-only agent, to be assigned after implementation per
  `docs/MULTI_AGENT.md`. No independent role is claimed until that work occurs.
- Repair limit: two cycles for the same finding; third recurrence escalates to owner.
- Stop: deliver a separate owner-review PR, then stop before Finding 3. Owner alone merges.

## Verification plan

Add regressions first and capture PostgreSQL RED before changing production code.
Use existing CI with only this exact branch enabled; keep the audit reproduction branch
intact. Then add the smallest shared-helper guard, run targeted tests and the full suite,
inspect exact checkout SHA/runtime/logs and record independent Scrutinize before opening PR.
No local PostgreSQL runtime is currently configured; local lint is supplementary only.
