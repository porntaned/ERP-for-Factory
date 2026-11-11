# Repository instructions

## Purpose

Build a public portfolio ERP for a fictional LED assembly factory with synthetic data. Start with a Django modular monolith and PostgreSQL. The owner reviews and merges changes.

## Issue workflow

1. Confirm repository, branch, HEAD and working state. Fetch every branch ref first
   (`git fetch --depth=50 origin '+refs/heads/*:refs/remotes/origin/*'`) and list remote
   branches not merged into `main`, so stale or parallel work is not missed.
2. Read the current GitHub issue and relevant checklist tasks.
3. State scope, exclusions, dependencies and acceptance criteria.
4. Make the smallest change that satisfies the issue.
5. Update progress only when linked evidence exists.

## Safety boundaries

- Work only in `porntaned/ERP-for-Factory`.
- Use a feature branch; never force-push, merge or deploy automatically.
- Never publish secrets, credentials, personal data or real factory data.
- Do not add unrelated features or significant dependencies without an approved issue.
- Real data, stock adjustments, valuation, privileged access and PLC/SCADA integration require explicit owner approval.

## Verification

- Test business behavior and database constraints meaningfully.
- Verify PostgreSQL-specific claims on PostgreSQL. SQLite or mocks are not equivalent evidence.
- Run targeted tests, diagnose root causes, then run relevant regression checks.
- Follow `docs/SCRUTINIZE.md` before opening a pull request.
- Record actual commands, environment and results. For local development checks, record the
  commit they ran on.
- CI on PostgreSQL 18.6 is the evidence of record. CI posts its results (commit SHA, server
  version, test counts) as a commit comment and one updated PR comment. While the PR is open,
  cite that comment by link only: it always shows the latest head. Do not push a commit
  whose only purpose is to record a CI result or SHA of the same PR. The CI SHA and run go
  into the post-merge docs PR.
- Documentation-only commits after a review need no new review and no new evidence commit.
  The CI comment on the final head covers them. Say in the PR body which commits were
  documentation only.
- Local runs on other versions are development checks only and must be labelled as such.
- Label self-review and independent review accurately.

## Domain ownership

- Inventory owns stock quantities and movements.
- Quality owns inspection decisions; Inventory enforces movement eligibility.
- Manufacturing uses Inventory interfaces for issues, returns, consumption and output.
- Accounting owns valuation and financial posting.
- Posted movements retain history; corrections reference the original transaction.

## Documentation updates

Documentation must describe `main` as it is. The agent that prepares a change also prepares
its documentation in the same PR. Status that can only be known after the owner merges
(merge SHA, post-merge `main` CI, checklist ticks) is updated **immediately after the merge,
before any other work starts**: the agent that performed or observed the merge opens a small
follow-up docs PR that references it, in the same session. A merge is not finished until
that docs PR is open.

1. `docs/TASKS.md`: check an item only when linked evidence exists; update **สถานะปัจจุบัน**
   and add a dated Progress log line (what merged, merge SHA, CI run, review type, what remains).
2. The slice's record in `docs/assignments/<slice>.md`: scope, actual commands and results of
   development checks (with the commit they ran on), review status and a link to the PR's CI
   comment; then a closeout section in the post-merge docs PR (merge SHA, PR and `main` CI run
   with SHA and test counts). (Issues up to #29 keep their
   evidence in `docs/evidence/`; review records go in `docs/reviews/`; only files named `*-independent-review.md` are independent reviews, and every review file states its type on its first lines.)
3. `README.md`: change only when the delivered / not-delivered summary changes. Never pin a
   commit SHA there; point to TASKS.md.
4. Any other document whose described behavior or setup the change affects (`DEVELOPMENT.md`,
   `PROJECT.md`, this file) is updated in the same PR.
5. Correct stale statements instead of deleting them: mark them historical with a date.
6. Every PR fills in the documentation checklist in `.github/pull_request_template.md`.
