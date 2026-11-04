# Repository instructions

## Purpose

Build a public portfolio ERP for a fictional LED assembly factory with synthetic data. Start with a Django modular monolith and PostgreSQL. The owner reviews and merges changes.

## Issue workflow

1. Confirm repository, branch, HEAD and working state.
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
- Record actual commands, environment, results and tested commit SHA.
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
2. The slice's record in `docs/assignments/<slice>.md`: scope, tested SHA, actual commands and
   results, review status, then a closeout section after merge. (Issues up to #29 keep their
   evidence in `docs/evidence/`; independent reviews go in `docs/reviews/`.)
3. `README.md`: change only when the delivered / not-delivered summary changes. Never pin a
   commit SHA there; point to TASKS.md.
4. Any other document whose described behavior or setup the change affects (`DEVELOPMENT.md`,
   `PROJECT.md`, this file) is updated in the same PR.
5. Correct stale statements instead of deleting them: mark them historical with a date.
6. Every PR fills in the documentation checklist in `.github/pull_request_template.md`.
