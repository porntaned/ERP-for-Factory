# Docs repair after M6 (2026-11-11)

Type: documentation only. Status: **PR open, awaiting the owner** (no merge, no deployment).

## Roles (as performed)

- **Manager:** the Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby` (branch `claude/vibrant-sagan-ivztik`).
  It made these edits itself; no sub-agent was used and there is no review (self-checked only).
- **Owner:** gave the task list in chat (2026-11-11) and decides the merge.

## Scope (owner's list)

1. Record the merge of [PR #115](https://github.com/porntaned/ERP-for-Factory/pull/115) at `217be3f` and
   [main CI #281](https://github.com/porntaned/ERP-for-Factory/actions/runs/43004892638) in `docs/TASKS.md`.
2. `README.md` screen list: add `/quality/`, `/quality/audit/`, `/lots/search/`, `/lots/<id>/trace/`.
3. Missing CI links in `docs/TASKS.md`: M6.2 (main CI #257), PR #106 (PR CI #261), PR #107 (main CI #266).
4. `m62` / `m63` records: the statements that Issue #103 / #108 are still open are marked historical with a date.
5. Two broken links in `docs/reviews/project-audit-after-pr12.md`: copy `docs/evidence/pr-12-merged.jpg` and the
   reproduction tests (as `docs/evidence/project-audit-reproductions.py.txt`, not under `tests/`) from branch
   `codex/project-audit-after-pr12` (`98103b2`).

Excluded: M7 work, code, tests, `AGENTS.md`, `docs/MULTI_AGENT.md`, branch/tag clean-up.

## Facts checked before editing (GitHub, 2026-11-11)

- Open PRs: none. Open Issues: none. Issue #103 closed (completed) 2026-11-10; Issue #108 closed (completed) 2026-11-11.
- Run numbers match the owner's list: #257 → `66c0ede` (push, main), #261 → `47f6f99` (PR #106 head),
  #266 → `94a3e38` (push, main, PR #107 merge), #280 → `d6555cc` (PR #115 head), #281 → `217be3f` (push, main).
- Test counts read from each run's `postgresql-tdd` job log (last pytest summary line): #281 `1160 passed`,
  #266 `1067 passed`, #261 `1067 passed`; PostgreSQL `18.6 (Debian 18.6-1.pgdg12+2)`, Python 3.14.8.
  The CI summary artifact could not be downloaded (the session's network proxy refused the artifact host), so
  the job logs were used instead.
- The copied files are byte copies of the blobs at `98103b2` (`git show <ref>:<path>`); the image is 58,667 bytes.
- `/quality/`, `/quality/audit/`, `/lots/search/`, `/lots/<int:pk>/trace/` exist in `config/urls.py`;
  all are `login_required`; `/quality/audit/` raises 403 without a QUALITY or APPROVER grant.

## Development checks (local, not CI; base `main` at `217be3f`, working tree before the commit)

- A small relative-link checker (session scratchpad, not committed) over the six changed Markdown files:
  on `main` `217be3f` `docs/reviews/project-audit-after-pr12.md` has **2 broken relative links**
  (`../evidence/pr-12-merged.jpg`, `../../tests/quality/test_project_audit_reproductions.py`); with this change
  all six files have **0 broken relative links**.
- `git diff --check`: no whitespace errors.
- No code, test or migration changed, so pytest/Ruff were not run locally; CI runs the full suite on PostgreSQL 18.6.

## Evidence

CI evidence of record: the PR's CI comment (linked from the PR once CI has run).
