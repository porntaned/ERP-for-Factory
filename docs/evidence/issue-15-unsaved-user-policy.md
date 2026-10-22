# Issue #15 — PostgreSQL evidence

Scope: audit Finding 2 only. Repository `porntaned/ERP-for-Factory`, branch
`codex/fix-unsaved-user-policy`, base main `eba63622495c6b065ad0abcd8e652676f9189d20`.
Manager/implementer `/root` inspected actual GitHub Actions output through the prepared
browser; this is self-verification. No local PostgreSQL execution is claimed.

## Recovery and scope

PR #14 is merged and Issue #13 is completed. Main remained at `eba6362` when rechecked
through the browser on 2026-10-22. No open PR existed before this delivery. Finding 1
was not reimplemented. Its persisted-active predicates and tests remain intact.

## RED

- Tested commit: `7c9c1ac81beaa71776516e5aea29c9d7bc3e7288` (test-only production tree).
- [Foundation #57](https://github.com/porntaned/ERP-for-Factory/actions/runs/39587274206),
  [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39587274206/job/119179186227).
- `uv run pytest -q --tb=short`: **2 failed, 268 passed in 4.68s**.
- Both failures are the `matching` parameters in the new module: the boolean policy
  returns True; the Warehouse QuerySet returns a Warehouse instead of an empty result.
- Saved/ORM-loaded positive controls and all nonmatching/absent-PK cases pass. The retained
  Finding 1 targeted module passes **3 tests in 0.53s**.
- The separately configured unsaved-user targeted step was after the full suite at RED
  and was skipped after that expected failure; the full suite executed all six new cases.
- [Browser DOM capture](issue-15-red-browser.txt) includes actual assertions, runtime
  and the run overview linking this exact test commit to the failed job.

## GREEN

- Tested implementation: `d132237211c5abdc509679da91b7b12566dff38c`.
- [Foundation #58](https://github.com/porntaned/ERP-for-Factory/actions/runs/39587682335),
  [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/39587682335/job/119180557787).
- Finding 1 targeted module: **3 passed in 0.47s**.
- Finding 2 targeted module: **6 passed in 0.37s**.
- Full suite: **270 passed in 3.17s**.
- Django configuration: no issues. Migration drift: no changes. Fresh migrations applied
  successfully. Ruff passed. All prerequisites and test steps succeeded.
- [Browser DOM captures](issue-15-green-browser.txt) record checkout SHA, versions,
  commands/results and fresh migrations; captured from the browser, not a raw-log export.
- Production change is only `and not user._state.adding` in the shared helper. The
  Finding 2 targeted CI step now precedes the full suite; no schema/dependency changes.

## Environment and actual commands

GitHub-hosted Ubuntu 24.04; Python 3.14.8; Django 5.2.18; psycopg 3.3.6;
PostgreSQL `18.6 (Debian 18.6-1.pgdg12+2)`. CI verifies vendor `postgresql` and prints
the live server version. Tests use synthetic users with unusable passwords and real
saved grants/Organization/Plant/Warehouse rows.

```text
uv python install 3.14.8
uv sync --locked --all-groups
uv run python --version
uv run python -c "import django, psycopg; print('Django', django.get_version()); print('psycopg', psycopg.__version__)"
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run ruff check .
uv run pytest -q tests/access_control/test_persisted_deactivation.py --tb=short
uv run pytest -q tests/access_control/test_unsaved_user_policy.py --tb=short
uv run pytest -q --tb=short
```

The PostgreSQL connection/version command is retained in
[the workflow](../../.github/workflows/foundation.yml). Local supplemental checks:
`.venv/Scripts/ruff.exe check .` and `git diff --check` passed; they are not PostgreSQL evidence.

## Scrutinize and boundary

Independent reviewer `/root/issue15_final_review` traced the exact implementation and
independently inspected these browser captures; verdict **ship** —
[independent report](../reviews/issue-15-unsaved-user-policy-independent-review.md).
This is not independent PostgreSQL execution or direct reviewer retrieval from GitHub.

The guard checks ordinary Django instance state; it is not an authentication mechanism
against trusted Python code deliberately modifying internal state. Already-evaluated
QuerySet caches and a later write after a policy read are outside this read contract.
No HTTP exploit, deployment or production security validation is claimed. Findings 3–5
remain outstanding; the separate RED audit branch remains intact.

Delivery ends at an owner-review PR. Only the owner can merge or deploy.

## Owner-review delivery

- [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16), opened through the
  prepared browser on 2026-10-22 — [visible proof](issue-15-pr.jpg).
- Documentation head `06749d0ec9ab7898133733f3066f45dbf2af8a9b`:
  [Foundation #59](https://github.com/porntaned/ERP-for-Factory/actions/runs/39715723123)
  succeeded; manager inspected the browser run summary. The detailed test results above
  belong to implementation commit `d132237`, not a claim of another independently executed run.
- Final documentation links and diff were checked. Subsequent changes only link this
  delivery and record the screenshot; code/tests/workflow are unchanged from `d132237`.
- Issue remains open for owner review/merge. PA.4 and owner acceptance stay unchecked.
  No merge, deployment or Finding 3 work performed.

## Owner-authorized merge

On 2026-10-22, after owner instruction to proceed and merge first when needed, the
manager rechecked PR #16 through the prepared browser. Head remained
`6d8479350ec4324a5f8c7fcd9c4637a50492e5b7`, both checks passed and GitHub reported
no base-branch conflicts. Independent implementation verdict remained `ship`; all
changes after reviewed implementation `d132237` were documentation only.

- [PR #16](https://github.com/porntaned/ERP-for-Factory/pull/16) merged with an ordinary
  merge commit: [`c62687b7ed60515de9424e69fe22ef43bbdfe81e`](https://github.com/porntaned/ERP-for-Factory/commit/c62687b7ed60515de9424e69fe22ef43bbdfe81e).
- [Issue #15](https://github.com/porntaned/ERP-for-Factory/issues/15) refreshed in the
  browser and confirmed Closed/completed; closing linkage points to PR #16.
- [Visible merge proof](issue-15-merged.jpg).
- `git fetch origin` retrieved the merge; `git rev-parse origin/main` returned the exact
  merge SHA. `git diff --stat 6d8479350ec4324a5f8c7fcd9c4637a50492e5b7 origin/main`
  was empty: merged main has the identical tree to the checked PR head.
- No separate PostgreSQL execution at the merge commit is claimed. The identical tree
  preserves the previously inspected PostgreSQL/CI evidence.
- PA.4 and PA.4.5 are now complete. Finding 3 remains unstarted pending scope confirmation;
  there was no deployment. The preceding owner-review delivery section records the
  historical pre-merge handoff, not the current issue state.
