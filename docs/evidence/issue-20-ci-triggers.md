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

This and the next section describe the historical pre-merge handoff. The owner action
and actual main-push observation below supersede their pending status.

Main's literal matching is statically reviewed; an actual main push can be observed only after owner-authorized
merge. No main push or merge is manufactured for verification. Push and PR runs on
the same feature commit can both execute; reducing duplicate runs is outside this issue.
Other branch prefixes and tags are intentionally outside the stated trigger contract.

Self-review finds no blocking defect in the minimal event change; independent
Scrutinize is [recorded separately](../reviews/issue-20-ci-triggers-independent-review.md).
PA.6 remains incomplete until owner acceptance; Finding 5/README is unstarted.
No merge or deployment.

## Owner-review PR and actual PR event

- [PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21) is Open, targeting main
  from `codex/ci/general-triggers`; [visible proof](issue-20-pr.jpg).
- Actual `pull_request` opened event: [run 39722800434](https://github.com/porntaned/ERP-for-Factory/actions/runs/39722800434),
  job 119639878305, **Success, 281 passed in 5.52s**.
- Source head `08e45b416ecb65f6ab7d09adcfba6c0a0a091b4a`; checkout tested the synthetic
  merge ref `2dfc5aeb0ec5b64c99e5641aea0578e41a5c1426`, not a later documentation commit.
- [PR browser capture](issue-20-pr-browser.txt) records checkout SHA, actual event and
  successful completed full suite. Earlier intermediate snapshots are followed by the
  completed output. PR base main is visible in the screenshot and unchanged configuration.
- Independent reviewer inspected the captured PR evidence and documentation through
  `08e45b4`, returning `ship` for handoff. No reviewer live retrieval or separate DB run.
- Final bookkeeping changes only evidence, review, assignment and checklist. Workflow
  remains identical to reviewed implementation `56a0d80`. Latest-head CI is checked in
  the PR before handoff; the historical run above is not relabelled as testing that head.
- Next responsible role: owner review, acceptance/merge decision and actual main-push
  observation after any authorized merge. Issue #20 and PA.6 stay pending that gate.

## Owner-authorized merge and main push

The owner explicitly authorized merging PR #21. It merged through the prepared browser
on 2026-10-22 at [`a294080133cc31ee6ce0b0e1fc808280d669f203`](https://github.com/porntaned/ERP-for-Factory/commit/a294080133cc31ee6ce0b0e1fc808280d669f203).
[PR #21](https://github.com/porntaned/ERP-for-Factory/pull/21) is Merged;
[Issue #20](https://github.com/porntaned/ERP-for-Factory/issues/20) is Closed/completed.
[Visible merge proof](issue-20-merged.jpg).

The actual main push triggered [Foundation run 39724957324](https://github.com/porntaned/ERP-for-Factory/actions/runs/39724957324),
job 119646635081: **Success, 281 passed in 5.44s**. The summary links main and the exact
merge SHA above; the expanded connection step reports `vendor=postgresql` and
`server_version=18.6 (Debian 18.6-1.pgdg12+2)`.
[Selected visible browser evidence](issue-20-main-browser.txt).
All existing configuration/migration/Ruff/targeted steps completed; this report does
not invent individual targeted-result counts from their collapsed output.

Recovery for Issue #22 rechecked PR, Issue and main run through the browser and fetched
origin/main. `git diff --stat e82a0fe73bf1c0cd243840b79b6fed8bbb012656 origin/main`
was empty: the merged tree matches the checked PR head. The main result tests the actual
merge commit, not the subsequent documentation branch. This is manager self-verification,
not a new independent database execution. PA.6 is reconciled under Issue #22; no workflow
or application change is repeated, and no deployment occurred.
