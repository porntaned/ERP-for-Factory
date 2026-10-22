# Issue #20 — Foundation trigger evidence

- Repository: `porntaned/ERP-for-Factory`; [Issue #20](https://github.com/porntaned/ERP-for-Factory/issues/20).
- Base main: `95d612bc41b4bda184598ba30f7072c4896f976d`.
- Implementation: `56a0d80f05250751b3e5025b1c28ec5f6137d60c`.
- Manager/implementer/verifier: `/root`; browser CI inspection is self-verification.
- Environment: existing GitHub Actions Ubuntu 24.04 job and disposable PostgreSQL 18.6;
  no local database execution, deployment or production-data claim.

## Intent and trace — self-Scrutinize

Finding 4 is an event-selection defect: the old push filter listed eight historical
branch names, excluding future branches and main. Static inspection proves that
configuration gap; no failing business test or synthetic TDD RED is claimed.

The smallest change replaces that list with `main`, `'codex/**'`, `'feat/**'`.
The existing `pull_request` target remains main. Everything from `permissions` through
the last job step is unchanged, including action pins, runtime, dependency lock,
database service and tests. No application, schema, test body or README change.

[Official GitHub syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
was read in the prepared browser: push filters match ref names, `**` supports nested
paths, and pull-request branch filters match the base branch. The two deliberately
nested new refs below were absent from the former whitelist and use the same commit.

## Observed push events — 2026-10-22

| Ref | Actual run | Result |
| --- | --- | --- |
| `codex/ci/general-triggers` | [39722506487](https://github.com/porntaned/ERP-for-Factory/actions/runs/39722506487) | push, Success; 281 passed in 4.60s |
| `feat/ci-trigger-probe/issue-20` | [39722509071](https://github.com/porntaned/ERP-for-Factory/actions/runs/39722509071) | push, Success; 281 passed in 5.72s |

Both run summaries link exact commit `56a0d80f05250751b3e5025b1c28ec5f6137d60c`.
The probe needs no separate workflow edit or PR; its ref is retained for review.

- [Codex browser capture](issue-20-codex-browser.txt): successful job, full-suite output,
  runtime and PostgreSQL output, run summary with event/ref/commit.
- [Feat browser capture](issue-20-feat-browser.txt): successful run summary with
  event/ref/commit and successful job/full-suite output.
- Actual codex runtime output: Python 3.14.8, Django 5.2.18, psycopg 3.3.6,
  `vendor=postgresql`, `server_version=18.6 (Debian 18.6-1.pgdg12+2)`.
- Jobs completed all retained configuration, migration-state, fresh-migration, Ruff,
  persisted-deactivation, unsaved-user and event-identity regression steps. Those
  detailed step outputs were collapsed in these captures; full-suite and codex runtime
  outputs were expanded. No separate detailed targeted-result count is inferred.

## Actual commands and scope

Local: `git fetch origin`; `git switch -c codex/ci/general-triggers origin/main`;
`git diff --check`; commit; `git push -u origin codex/ci/general-triggers`;
`git push origin 56a0d80f05250751b3e5025b1c28ec5f6137d60c:refs/heads/feat/ci-trigger-probe/issue-20`.
No force push. Local diff checking passed.

CI retained commands: `uv sync --locked --all-groups`, runtime-version commands,
`uv run python manage.py check`, PostgreSQL connection/SHOW server_version,
`uv run python manage.py makemigrations --check --dry-run`,
`uv run python manage.py migrate --noinput`, `uv run ruff check .`,
the three existing targeted pytest commands and `uv run pytest -q --tb=short`.
Exact command bodies remain in [.github/workflows/foundation.yml](../../.github/workflows/foundation.yml).

## Limits and next gate

Actual PR-to-main event proof is pending PR creation. Main's literal matching is
statically reviewed; an actual main push can be observed only after owner-authorized
merge. No main push or merge is manufactured for verification. Push and PR runs on
the same feature commit can both execute; reducing duplicate runs is outside this issue.
Other branch prefixes and tags are intentionally outside the stated trigger contract.

Self-review finds no blocking defect in the minimal event change; independent
Scrutinize is recorded separately before the owner-review PR. PA.6 remains incomplete
until owner acceptance; Finding 5/README is unstarted. No merge or deployment.
