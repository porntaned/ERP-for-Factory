# Issue #22 — README/status evidence

- Repository: `porntaned/ERP-for-Factory`; [Issue #22](https://github.com/porntaned/ERP-for-Factory/issues/22).
- Branch: `codex/docs/readme-status`; base `a294080133cc31ee6ce0b0e1fc808280d669f203`.
- Implementation: `cf9f010d212261ddc2e2c8a23bc60dfdc18ebf7b`.
- Manager/implementer/verifier: `/root`; own source/browser checking is self-verification.
- Documentation only. No local PostgreSQL run or new business-behavior claim.

## Intent and trace — self-Scrutinize

Audit Finding 5 identifies README's obsolete PR #3/51-test current-status paragraph.
The smallest fix replaces that paragraph with dated main milestones, exact main CI,
links to evidence/checklist and the outstanding Finding 5 issue. Other README sections
are unchanged. Stock ledger/movement, Inventory UI, full inspection and deployment
remain undelivered; no M3 acceptance is inferred.

Git merge history confirms PRs #3, #6, #8, #10, #12 and Findings 1–4 (#14/#16/#19/#21).
`config/settings.py` registers facilities, catalog, inventory, access_control and quality;
source and TASKS distinguish the existing Lot/history foundations from unfinished MVPs.

Finding 4 reconciliation appends actual owner merge/main evidence and labels historical
pending handoffs. [PR #21 merge/main proof](issue-20-ci-triggers.md#owner-authorized-merge-and-main-push)
binds `a294080133cc31ee6ce0b0e1fc808280d669f203` to actual push/main, PostgreSQL 18.6,
281 passing tests and completed Issue #20. PA.6 is checked only with those links.
PA.7 stays pending owner acceptance; M3/M3.4 and all product milestones are unchanged.

## Documentation verification

- `git fetch origin`: main remains `a294080133cc31ee6ce0b0e1fc808280d669f203`.
  `git diff --stat e82a0fe73bf1c0cd243840b79b6fed8bbb012656 origin/main`: empty.
- `git diff --check`: passed before implementation commit.
- One-off Python standard-library check, run via PowerShell here-string piped to
  `.venv/Scripts/python.exe -`: read README, TASKS, Issue #20/#22 assignments and
  Issue #20 evidence; resolve local Markdown paths within repository and check ASCII
  heading anchors; reject obsolete README count and assert exact main/run/count.
  Result: **5 documents, 104 local targets passed; heading anchors resolved; obsolete
  README status removed and dated exact main evidence retained.** No new test or package.
- GitHub Preview rendered the source paragraph at implementation SHA, including all
  Thai text and resolved branch-relative evidence/TASKS links.
  [Rendered DOM excerpt](issue-22-readme-browser.txt), [preview screenshot](issue-22-readme-preview.jpg).
- Independent reviewer separately inspected source, git history and manager-captured
  evidence, checked 104 targets/anchors with PowerShell and diff checking, then returned
  [ship](../reviews/issue-22-readme-status-independent-review.md). No reviewer live
  GitHub retrieval or database run is claimed.

## Naturally triggered branch CI

Push of `cf9f010d212261ddc2e2c8a23bc60dfdc18ebf7b` triggered
[Foundation 39752889301](https://github.com/porntaned/ERP-for-Factory/actions/runs/39752889301),
job 119737549611, **Success; 281 passed in 8.35s**.
[Selected browser lines](issue-22-ci-browser.txt).
The existing PostgreSQL job and commands remain unchanged; this supplementary run is
separate from README's dated historical main evidence. Detailed connection/targeted
outputs were collapsed in this capture; no new specific runtime/count is inferred.
No failing business RED was invented for a documentation correction.

## Limits and next gate

This and the next section record the pre-merge handoff. The owner-authorized merge
below supersedes their pending PR/Issue status.

No repair cycle needed. Reviewer verdict applies to the implementation SHA, with the
rendered proof also inspected; later evidence/bookkeeping do not change the paragraph.
Final documentation gets diff/link checks. Stop at owner-review PR, keeping Issue #22
and PA.7 pending owner acceptance. No source/test/schema/workflow/dependency change,
M3 acceptance, Inventory work, merge or deployment in this task.

## Owner-review delivery

[PR #23](https://github.com/porntaned/ERP-for-Factory/pull/23) is Open, targeting main
from `codex/docs/readme-status`; [visible proof](issue-22-pr.jpg). It was opened after
self-verification and independent `ship`. Evidence/review commit
`c27165e46fcc45f7bc1ef4ed6170f3ed9332874f` does not change README or runtime files from
the reviewed implementation. Final handoff bookkeeping only adds the PR link/screenshot
and progress status. Final diff/link checking and latest-head PR checks are the last
manager checks before handoff; historical runs above retain their exact tested SHA.
Final local target/ASCII-anchor check after adding delivery links: **7 Markdown
documents, 117 targets passed**; diff checking passed and the README/runtime diff
from reviewed implementation remained empty.
Issue #22 and overall PA.7 remain pending owner review/merge. No merge, deployment or
next milestone work is performed.

## Owner-authorized merge

After owner approval, [PR #23](https://github.com/porntaned/ERP-for-Factory/pull/23)
merged through the prepared browser on 2026-10-22 at
[`e6cd22c9bddd533b40d293dbad509076ae41172c`](https://github.com/porntaned/ERP-for-Factory/commit/e6cd22c9bddd533b40d293dbad509076ae41172c).
[Issue #22](https://github.com/porntaned/ERP-for-Factory/issues/22) is Closed/completed.
[Visible merge proof](issue-22-merged.jpg).

Actual main push [Foundation 39754340827](https://github.com/porntaned/ERP-for-Factory/actions/runs/39754340827),
job 119742446278, succeeded with **281 passed in 5.52s** at that exact merge SHA.
It was re-inspected during separately authorized Issue #24; event/ref/runtime/result
are in [main proof](issue-24-main-ci-browser.txt). `git fetch origin` confirms main;
its tree equals PR head `d215f403932b6d5d9db2bc2a105508f039f1a7d0`.
This is manager self-verification, not a new independent database run. PA.7 is reconciled
in Issue #24 without repeating Finding 5. No deployment occurred.
