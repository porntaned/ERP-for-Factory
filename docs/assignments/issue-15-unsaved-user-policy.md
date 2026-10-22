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
- Preliminary reviewer: `/root/issue15_independent_review` (code trace before interruption).
- Final independent reviewer: `/root/issue15_final_review`, separate read-only agent;
  [Scrutinize report](../reviews/issue-15-unsaved-user-policy-independent-review.md), `ship`.
- Repair limit: two cycles for the same finding; third recurrence escalates to owner.
- Stop: deliver a separate owner-review PR, then stop before Finding 3. Owner alone merges.

## Verification plan

Add regressions first and capture PostgreSQL RED before changing production code.
Use existing CI with only this exact branch enabled; keep the audit reproduction branch
intact. Then add the smallest shared-helper guard, run targeted tests and the full suite,
inspect exact checkout SHA/runtime/logs and record independent Scrutinize before opening PR.
No local PostgreSQL runtime is currently configured; local lint is supplementary only.

## Handoff evidence

- Test commit: `7c9c1ac81beaa71776516e5aea29c9d7bc3e7288`; PostgreSQL RED **2 failed,
  268 passed**. Implementation/reviewed commit: `d132237211c5abdc509679da91b7b12566dff38c`;
  targeted **6 passed**, persisted-deactivation **3 passed**, full suite **270 passed**.
- [Actual commands, runtime, results and CI links](../evidence/issue-15-unsaved-user-policy.md).
- Production diff: one shared-helper guard. New tests exercise both public interfaces
  with three PK states and saved/ORM-loaded authorized controls. CI enablement is exact
  branch only; no general trigger fix is claimed.
- Manager implemented and self-verified using prepared-browser CI inspection. Independent
  reviewer inspected source and captured browser evidence; no separate database execution.
- No repair cycle required. Remaining work is owner review/merge after the separate PR.
  Finding 3 and other audit work are excluded. No merge or deployment performed.

## Delivery and stop

[PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16) opened through the prepared
browser on 2026-10-22, base `main`, head `codex/fix-unsaved-user-policy` —
[visible proof](../evidence/issue-15-pr.jpg). Documentation head
`06749d0ec9ab7898133733f3066f45dbf2af8a9b` passed
[Foundation #59](https://github.com/porntaned/ERP-for-Factory/actions/runs/39715723123).
Later delivery bookkeeping changes only documentation and the PR screenshot.
Implementation/tests/workflow remain identical to reviewed GREEN commit `d132237`.
PA.4 and Finding 2 owner acceptance remain unchecked until the owner merges.
Work stops here with the next responsibility assigned to the owner; Issue #15 stays open.
