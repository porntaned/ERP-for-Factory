# Review — PR #114 (Issue #113, M6.4: QC quantities, concurrency and audit)

**Type: independent review by a separate session** (Claude Code session `session_01MVmjhbj9fzvhv1zzX1M15j`,
created by the Manager session; read-only, Scrutinize per `docs/SCRUTINIZE.md`). It is not an owner review.
Date 2026-11-11. Reviewed head `bda9441` (branch `claude/keen-feynman-jkijlw`), base `main` `3b8dac1`.
Spec: `docs/assignments/m64-qc-hardening-audit.md`.

The Reviewer was given only the PR number, the Issue number and the spec path. "Report" is the
Reviewer's message as received, copied by the Manager without edits other than restoring the `<`, `>`
and `&` characters that the message transport had escaped. "Manager disposition" is the Manager's own
and is not part of the review.

## Report

**Review type: independent review by a separate session** (Reviewer role, docs/MULTI_AGENT.md; read-only; no edits, commits, pushes or PR comments). PR #114, Issue #113, spec docs/assignments/m64-qc-hardening-audit.md. Reviewed head `bda9441` (base `main` `3b8dac1`).

### Intent
Close M6 by proving the QC commands hold at boundary sample quantities and under concurrent use, and add one read-only page listing every QC decision, plus LotInspection in the read-only admin. The change is small and fits the spec. I see no simpler approach: the page is one view, one form and one template, and the admin change is one line. No service, model, migration, role or grant changes (`git diff --stat` shows none in quality/services.py, models or migrations).

### What I traced and verified
- **Page** (`demo/quality_views.py:308-372`): access uses `quality_warehouses` (QUALITY/APPROVER), the same rule as `/quality/`, and raises 403 when the user has no warehouses. The warehouse choice queryset is limited to the user's warehouses, so another warehouse's id fails validation and the page shows a message and no rows. Keys come from one UNION ALL query ordered `-created_at, row_kind, -id`, sliced to offset + 51. Rows load with `in_bulk` and `select_related`, so the query count stays fixed (10 queries, bound 12 in the test). Paging copies `request.GET`, so filters carry over. `@require_GET` makes POST return 405. Templates autoescape. Nav (`base.html`) uses `can_quality` (`demo/permissions.py:21`), the same rule as the view.
- **Admin:** `register_read_only` takes `*models`, and `ReadOnlyAdmin` refuses add, change and delete.
- **Tests:** I read the race and revoke tests in `tests/quality/test_qc_hardening.py:128-300`. They use the existing two-connection helpers (`blocked_action`, `wait_for_lock`), hold the real Lot lock and call the real commands. The balance-lowered-first case uses `reverse_receipt`, and the test asserts that the waiting inspection is refused with the balance message and writes nothing. The Implementer's reasoning (a transfer out of a HOLD pair is refused by the RELEASED gate) matches the test, which asserts that `TransferQualityError` comes first. The date test disables the append-only triggers only inside that test's transaction, which rolls back.
- **Development check (not evidence of record):** PostgreSQL 16 (local cluster), Python 3.14, on `bda9441`: `UV_PYTHON=3.14 uv run --env-file .env pytest -q -x` → **1160 passed** in 288s. This matches the PR's count.
- **Demo walk in DEVELOPMENT.md, development check on the same commit:** after `seed_production_demo --reset`, through the Django test client:
  - Step 1: demo-quality gets 200 with 14 rows.
  - Step 2: `?warehouse=<FG>` shows 2 rows (one event, one inspection).
  - Step 3: a FAIL on LAMP-0001 at FG, then a return by demo-approver. The newest rows are REJECTED→HOLD (demo-approver), HOLD→REJECTED (#8) and the FAIL inspection (#8), in that order.
  - Step 4: demo-warehouse gets 403.
  - A note `<b>รอยขีด</b>` was rendered escaped.
  - `?date_from=…&date_to=` set to today returned 200. `?page=999999`, `?page=0` and `?date_from=9999-12-31` each returned 200 with no rows and no 500.
- **CI:** `postgresql-tdd` run 42994904962 was **in progress** when I checked. The PR has no CI comment yet, so I have no CI result to cite.

### Findings (most severe first)
No blocking or major defects. Minor and nit items:

1. **Minor, docs: the spec's status lines are stale at head.** `docs/assignments/m64-qc-hardening-audit.md:5` says "PR not opened". Line 9 says the Reviewer is "(not started)". Lines 133 and 212-213 say "Review: none yet" and "once the PR exists". *Why:* AGENTS.md requires docs to describe the slice accurately, and PR #114 is now open and reviewed. *Smallest change:* when you record this review, set line 5 to "PR #114 open; independent review: ship", update lines 9, 133 and 212 to match, mark the old text historical, and link the PR's CI comment once it is posted. That commit is docs-only, so it needs no new review.
2. **Minor, PR body:** the checkbox "[x] … CI evidence cited by link" is ticked, but no CI comment exists yet. *Smallest change:* untick it until the CI comment is posted, then add the link.
3. **Minor, docs:** `docs/reviews/m64-independent-review.md` is listed in the spec's Documentation section but does not exist on the branch yet. Expected at this stage. *Smallest change:* add it from this report and label it independent review on its first lines (AGENTS.md).
4. **Nit, performance, no change in this PR:** `created_at__date` (`demo/quality_views.py:317,319`) casts to a date in TIME_ZONE, so an index on `created_at` cannot serve the filter. The UNION scans both tables on every load, and the OFFSET grows with page depth. The query count is bounded but the row work is not. This is acceptable for the demo and the spec excludes m4 performance. If it matters later, use local-midnight `created_at__gte` / `__lt` bounds and keyset paging.
5. **Nit:** `quality_audit` evaluates the warehouse queryset twice: once in `list(...)` and once inside the form's ModelChoiceField. That costs one extra query and is harmless.
6. **Observation, pre-existing and out of scope:** the Lot link opens `/lots/<pk>/genealogy/` (`demo/production_views.py:82`). That page is login-only and lists inspections and events at every warehouse, so it is not scoped like the audit page. It was not changed here, and the spec asks for the link. Leave it to the owner if per-warehouse scoping is ever wanted.

### Verdict: **ship**
The biggest reason: every acceptance criterion traces to a test that runs the real command or view path on PostgreSQL. The page is scoped, read-only, escaped and query-bounded, and there are no rule, schema or permission changes. Findings 1-3 are documentation-only and can go in the commit that records this review. This holds only if CI on PostgreSQL 18.6 for the final head comes back green. It was still running when I finished.

## Manager disposition (Manager session, repair round 1 of 2, documentation only)

| # | Disposition |
|---|---|
| 1 | Fixed: spec status, Reviewer line, Evidence review line and CI link (CI comment posted after the review: [PR #114 CI comment](https://github.com/porntaned/ERP-for-Factory/pull/114#issuecomment-6792246771)). |
| 2 | Fixed: the PR body cites the CI comment by link; the box is now accurate. |
| 3 | Fixed: this file. |
| 4 | Not changed: nit; demo scale, and performance (m4) is out of scope by the spec. Recorded for a later Issue. |
| 5 | Not changed: nit, one harmless extra query within the tested bound. |
| 6 | Not changed: pre-existing and out of scope; left for the owner. |

Under AGENTS.md these documentation-only fixes need no new review.
