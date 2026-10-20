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

The first issue covers Organization → Plant → Warehouse schema and tests only.
