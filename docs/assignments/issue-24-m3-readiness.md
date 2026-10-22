# Issue #24 — M3 readiness before Inventory

- Repository: `porntaned/ERP-for-Factory`; [Issue #24](https://github.com/porntaned/ERP-for-Factory/issues/24).
- Owner authorization: main work item 2, verify readiness before Inventory. No M4 implementation.
- Branch: `codex/review/m3-readiness`; base main `e6cd22c9bddd533b40d293dbad509076ae41172c`.
- Recovery: correct remote, original `codex/docs/readme-status` head
  `d215f403932b6d5d9db2bc2a105508f039f1a7d0`, clean working tree; fetched main matches
  PR #23 merge tree. No open GitHub issue before #24. Completed implementation is reused.
- Scope: evidence matrix for M3.1–M3.4 and audit Findings 1–5; current source/interface
  trace and exact main PostgreSQL evidence; readiness limits; reconcile completed
  Finding 5/PR #23 status in TASKS and delivery evidence.
- Allowed files: documentation assignment/evidence/readiness/review and TASKS, selected
  captured proof, historical delivery status addenda. No runtime file changes.
- Acceptance: actual Issue criteria mapped to assignment, RED/GREEN, independent review,
  PR/merge and current seams; exact main SHA/runtime/results; all audit dispositions
  linked; new blockers reported if found; technical readiness and M4 boundaries stated;
  independent Scrutinize and owner-review PR. M3.4 needs existing evidence, not a new
  implementation. Overall M3 remains pending owner acceptance of this readiness PR.
- Manager/implementer/verifier: `/root`; own GitHub/source evidence checking is self-verification.
  Separate read-only reviewer follows MULTI_AGENT/SCRUTINIZE and is named after actual work.
- Dependencies: existing repository, prepared browser GitHub access, existing CI PostgreSQL.
  Reused main evidence is labelled; no local database run or new RED is invented.
- Exclusions: app/model/service/migration/test/workflow/dependency edits, M4/stock ledger,
  real data, stock adjustments, valuation, privileged integrations, force-push, merge, deploy.
  New confirmed code defects are blockers for separately scoped work, not silent repairs.
- Repair limit: two cycles for the same review finding; third recurrence stops for owner review.
- Stop: owner-review PR. Owner retains M3 readiness acceptance and permission for any later M4 issue.
