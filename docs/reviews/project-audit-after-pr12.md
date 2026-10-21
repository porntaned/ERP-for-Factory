# Whole-project Scrutinize after PR #12

## Snapshot, intent and method

- Date: 2026-10-21.
- Repository: `porntaned/ERP-for-Factory` only.
- Reviewed main: [`9b1d182eb6867b70f076e95a63dc03f1814f00ec`](https://github.com/porntaned/ERP-for-Factory/commit/9b1d182eb6867b70f076e95a63dc03f1814f00ec).
- [PR #12](https://github.com/porntaned/ERP-for-Factory/pull/12) merged with owner authorization;
  [Issue #11](https://github.com/porntaned/ERP-for-Factory/issues/11) closed as completed.
- Merge proof: [GitHub UI](../evidence/pr-12-merged.jpg).
- Review/evidence branch: `codex/project-audit-after-pr12`; no production fix or deployment in this audit.
- Manager/verifier: `/root`.
- Independent Quality reviewer: `/root/audit_quality_integrity`.
- Independent access/schema reviewer: `/root/audit_access_schema`.
- Independent CI/config/documentation reviewer: `/root/audit_ci_docs`.

Goal: check whether the implemented ERP foundation preserves its documented identity, permission
and audit contracts after merge, and identify concrete defects before Inventory development.

Simpler alternative: retain the existing Django modular monolith, typed history and two permission
functions. The findings require focused fixes and better edge-case tests, not a new framework.
Unimplemented M4–M7 features are planned scope, not regressions in this audit.

The reviewers followed [Scrutinize](../SCRUTINIZE.md) through real call paths and unchanged seams.
The PostgreSQL locking guidance from `supabase-postgres-best-practices` was used as supporting
review guidance; this project does not use or require a Supabase service.

## Actual execution evidence

- Baseline main tree is identical to PR head `52b9bcd3640ed19cdd9cba082583166ac73510c4` (`git diff --stat` empty).
- Prior PR-head [Foundation #46](https://github.com/porntaned/ERP-for-Factory/actions/runs/39529517577)
  and push #45 were GREEN.
- Reproduction commit: [`498e0c86181a3bef9d6b7a63e87d031ae832a1e1`](https://github.com/porntaned/ERP-for-Factory/commit/498e0c86181a3bef9d6b7a63e87d031ae832a1e1).
- [Foundation #47](https://github.com/porntaned/ERP-for-Factory/actions/runs/39540468833),
  [job logs](https://github.com/porntaned/ERP-for-Factory/actions/runs/39540468833/job/119026777844).
- Environment: GitHub-hosted Ubuntu 24.04, Python 3.14.8, Django 5.2.18, psycopg 3.3.6,
  PostgreSQL `18.6 (Debian 18.6-1.pgdg12+2)`.
- Commands: existing workflow `uv sync --locked --all-groups`, runtime/version prints,
  `uv run python manage.py check`, PostgreSQL vendor/server check,
  `uv run python manage.py makemigrations --check --dry-run`,
  `uv run python manage.py migrate --noinput`, `uv run ruff check .`,
  `uv run pytest -q --tb=short`.
- Configuration, PostgreSQL, migration drift, fresh migrations and Ruff passed.
- Result: **`5 failed, 261 passed in 5.16s`**. All five failures are the new reproductions below.
- Production files are unchanged from the reviewed main. The reproduction commit only adds the
  audit test module and this audit branch to the existing push trigger whitelist.
- Tests: [audit reproductions](../../tests/quality/test_project_audit_reproductions.py).

The audit branch is deliberately RED and is **not a merge-ready change**. No failing test was
skipped, xfailed or weakened. These are additional counterexamples to the existing 261 passing
tests. `/root` verified the PostgreSQL logs; the independent reviewers primarily traced code.
The access reviewer also ran an isolated SQLite in-memory policy reproduction, but that is not
used as PostgreSQL constraint evidence; Run #47 supplies the PostgreSQL proof.

## Finding 1 — P1: persisted deactivation does not revoke cached-user policy access

- **Location:** `access_control/policies.py:31`, `:54`, `:66` at reviewed main.
- **Why it matters:** a caller retaining an earlier User instance can continue to pass the shared
  Warehouse permission boundary after the persisted user is deactivated.
- **Trace:** `_is_operational_user` trusts `user.is_active` in memory; both public policies query
  assignment rows by user PK without filtering the persisted User's active state.
- **PostgreSQL proof:** retain an active instance, deactivate its row with a separate ORM UPDATE,
  then call `has_warehouse_role` / `warehouses_for_user`. Both deny assertions fail because the
  boolean still returns True and the Warehouse query still has a row (two new failures).
- **Suggested change:** add persisted-active filtering to both queries, retaining fail-closed input
  checks, and keep the separate-instance regression tests.
- **Boundary:** preexisting M3.2 defect. Quality transition independently locks/reloads its actor,
  so this does not show a stale-user bypass of the repaired Quality write command.

## Finding 2 — P2: an unsaved User with a matching PK passes the shared policies

- **Location:** `access_control/policies.py:31`–`:36` at reviewed main.
- **Why it matters:** the documented contract that unsaved users are denied is false; merely
  populating a primary key is treated as proof that the caller's model instance was saved.
- **PostgreSQL proof:** grant a saved user QUALITY, then construct a never-saved User with that
  PK. `_state.adding` is True, yet both policy deny assertions fail (two new failures).
- **Suggested change:** reject `_state.adding` in the shared helper and keep manual-PK unsaved
  regressions for both public interfaces. Persisted-active checks from Finding 1 remain necessary.
- **Boundary:** preexisting M3.2 defect, not a demonstrated HTTP authentication exploit; no login
  or API exists in this project. The Quality write command already rejects this input.

## Finding 3 — P2: an accepted high event ID blocks a later legitimate HOLD

- **Location:** `quality/migrations/0002_preserve_history_identity.py:48`,
  `quality/migrations/0001_initial.py:22`, `quality/services.py:159`.
- **Why it matters:** after a valid direct release insert, the normal Quality service can repeatedly
  fail to place that pair on HOLD because its generated IDs remain below the supplied ID.
- **Trace:** BigAutoField permits caller-supplied IDs; such an insert does not advance the normal
  sequence. The v2 trigger accepts a first event with high ID. The next service event receives
  a lower generated ID and is rejected by the monotonic-order guard.
- **PostgreSQL proof:** directly insert HOLD → RELEASED with ID 1,000,000,000; confirm the getter
  returns RELEASED; submit RELEASED → HOLD through the authorized service. It raises
  `IntegrityError: disposition event id must increase within its history` (one new failure).
- **Suggested change:** prevent ordinary caller-supplied IDs at the database boundary, e.g. an
  ALWAYS identity migration, and test high-ID rejection plus successful normal release/hold.
  Alternatively allocate authoritative IDs safely under the lock. Preserve existing migration
  history and verify forward/reverse behavior with the revised ID contract.
- **Boundary:** requires a direct database/ORM insert, not the service API. Ordinary input through
  the existing service alone does not expose an event-ID parameter. The original descending-ID
  regression remains useful but does not cover this accepted-high-ID case.

## Finding 4 — P3: push CI depends on historical branch names

- **Location:** `.github/workflows/foundation.yml:4`–`:10` at reviewed main.
- **Why it matters:** a newly named feature branch does not receive pre-PR PostgreSQL RED/GREEN
  evidence without editing workflow configuration. Merge pushes to main do not run this workflow.
- **Evidence:** the push list contains five exact historic names; PRs targeting main do run. This
  audit itself needed an explicit audit-branch whitelist entry for Run #47.
- **Suggested change:** use approved feature-prefix patterns such as `codex/**`, `feat/**`, and
  include main if post-merge verification is required. Keep the PR-to-main trigger.
- **Verification:** static trigger inspection, not a claim that existing PR checks were absent.

## Finding 5 — P3: README's current-status paragraph is obsolete

- **Location:** `README.md:7` at reviewed main.
- **Why it matters:** visitors see only PR #3 and 51 tests as current, while Item/UOM, Lot,
  permissions and Quality are already present. This weakens the portfolio's evidence story.
- **Evidence:** `config/settings.py:20`–`:24` registers those modules; the baseline suite has
  261 cases and PR #12 is merged.
- **Suggested change:** replace the single status paragraph with the merged milestone and links
  to current evidence/checklist, including the outstanding audit findings.

## Coverage, limitations and next work

Reviewed Organization/Plant/Warehouse, Item/UOM, Lot, grants/policies, Quality model/services,
both Quality migrations, real transaction paths, original/reproduction tests, Django config,
dependency pins/lock, workflow, setup guidance and review/checklist claims. Relative documentation
links checked by the CI/docs reviewer had no missing targets. No additional confirmed schema or
configuration defect was found in those inspected surfaces.

This was not an external penetration test, Git-history secret audit, dependency-vulnerability
database scan, load test, or deployed factory validation. No real factory data or live stock was used.
The absence of stock ledger, UI and inspections is planned work; it does not become a new bug here.

Proposed fix order: shared persisted-user policy checks (Findings 1–2), safe event ID generation
(Finding 3), then CI and README maintenance (Findings 4–5). Keep separate Issues/PRs and require
targeted PostgreSQL regressions plus the full suite before the next owner merge decision.

**Verdict: fix-then-ship — the shared permission boundary still accepts deactivated/unsaved
principals, and the new PostgreSQL counterexamples are unresolved.**
