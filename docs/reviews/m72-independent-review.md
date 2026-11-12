Type: independent review by a separate session (session_01MVmjhffM5mrrwnjZ2VDjRz); reviewed commit `2277b719d76ba17c5bad2833de2afee27878c3f3` (PR #118 head, branch `claude/vibrant-sagan-ivztik`), base `main` `1261e86`.

The Reviewer session was created by the Manager session (`session_01MVmjhdAZRZbr6kL22x7hby`) and was given only the
PR number, the Issue number and the spec path (plus the Reviewer role rules: read-only, Scrutinize, no merge, no
GitHub comments). "Report" below is the Reviewer's final message as received (2026-11-12), copied by the Manager
without edits. "Manager disposition" is the Manager's own and is not part of the review.

## Report

# Review: PR #118 (Issue #117, M7.2: install guide checked from a fresh state)

**Type: independent review by a separate session.** Claude Code session `session_01MVmjhffM5mrrwnjZ2VDjRz`, Reviewer role (`docs/MULTI_AGENT.md`), read-only, following `docs/SCRUTINIZE.md`. This is not an owner review. I made no edits, commits, pushes or GitHub comments.
**Date:** 2026-11-12.
**Reviewed head:** `2277b719d76ba17c5bad2833de2afee27878c3f3` (branch `claude/vibrant-sagan-ivztik`).
**Base:** `main` `1261e86a5dbd396dd9f10234e44e353829cebcc6`.
**Spec:** `docs/assignments/m72-install-guide.md`.
**Inputs:** PR #118, Issue #117 and the spec path. I read the repository and GitHub myself.

## Repository state (Issue workflow step 1)

- I ran `git fetch --depth=50 origin '+refs/heads/*:refs/remotes/origin/*'`. Then `git rev-parse --is-shallow-repository` printed `false`.
- Local `HEAD` and `origin/claude/vibrant-sagan-ivztik` are both `2277b71`, the same as the PR head.
- Six remote branches are not merged into `main`: `claude/docs-post-merge-105-106`, `claude/vibrant-sagan-ivztik` (this PR), `codex/docs/m43-closeout`, `codex/docs/project-ai-handoff`, `codex/inventory/concurrent-commands` and `codex/project-audit-after-pr12`.
  - The Issue's table counts 5, which matches once this PR's own branch is left out.
  - None of the other five touches M7.2.
- The PR has 6 commits (`c17fe90` → `2277b71`) and changes 5 files: +612 / −19.

## Intent

The goal is one install guide that takes a visitor from nothing to the running demo, proven from a fresh state by a CI job on PostgreSQL 18.6.

The change should exist. Before it, README used bash and DEVELOPMENT.md used PowerShell, and they disagreed. Neither said the role needs `CREATEDB` or mentioned `seed_production_demo`.

**A simpler alternative I considered:** CI could pull the guide's ` ```bash ` blocks out of `INSTALL.md` and run them directly, so the two could never drift apart.
- I don't ask for that now. The owner's rulings ask for an explicit job with `# CI-only:` differences that the reviewer compares line by line, and that is what the PR does.
- But the "character for character" match only holds at this commit, and nothing enforces it later. See finding 3.

## What I traced and verified

1. **The guide's commands match the CI job.**
   - I extracted every ` ```bash ` block of `docs/INSTALL.md` with `awk`, and every `run:` line of `jobs.install-guide.steps` by parsing YAML. Then I diffed the two.
   - The only differences:
     - the 7 `export` lines of step 2, replaced by the job `env`;
     - `git clone …` and `cd ERP-for-Factory`, replaced by `actions/checkout`;
     - the `runserver` line, replaced by the background run with HTTP checks;
     - the extra seed-rerun step;
     - the `if: failure()` log step.
   - Everything else matches character for character and in order. That includes the `psql` heredoc: the YAML block scalar strips the indentation, so `SQL` ends at column 0. It also includes the `sed` command and `printf … | set_demo_passwords --password-stdin`.
   - Each difference has a `# CI-only:` comment and is listed in spec items 1–7. The job uses `setup-uv` instead of a hand install; that is also marked and listed (item 1).

2. **The existing jobs are unchanged.**
   - `head -c 7070` of the new `foundation.yml` is byte-identical to `main`'s whole file (7070 bytes), checked with `cmp`.
   - `git diff --numstat` shows `130 0` for that file.
   - Parsed with YAML, `postgresql-tdd`, `report`, `name`, `on` and `permissions` equal `main`'s.
   - `report` still `needs: postgresql-tdd` only. The new job inherits the top-level `permissions: contents: read`.

3. **The only image is `postgres:18.6-bookworm`.**
   - Both jobs use that image (`foundation.yml:22` and `:205`).
   - The CI log of job `install-guide` shows only `docker pull postgres:18.6-bookworm`.
   - The `setup-uv` and `checkout` actions are the pins already used by `postgresql-tdd`.

4. **CI evidence on PostgreSQL 18.6.**
   - Run [#286](https://github.com/porntaned/ERP-for-Factory/actions/runs/43198580663) on head `2277b71`, tested as merge `062de6e`:
     - [`postgresql-tdd`](https://github.com/porntaned/ERP-for-Factory/actions/runs/43198580663/job/131115776495): success;
     - [`install-guide`](https://github.com/porntaned/ERP-for-Factory/actions/runs/43198580663/job/131115776822): success, 2m43s;
     - `report`: success.
   - The [PR CI comment](https://github.com/porntaned/ERP-for-Factory/pull/118#issuecomment-6820950684) shows `18.6 (Debian 18.6-1.pgdg12+2)`, Python `3.14.8` and **1160 passed**. That comment covers `postgresql-tdd` only.
   - I read the `install-guide` job log myself. In order:
     - `git version 2.56.0` and `uv 0.13.1`;
     - `18.6 (Debian 18.6-1.pgdg12+2)`, `CREATE ROLE`, `CREATE DATABASE`;
     - `Installed Python 3.14.8`, `Installed 12 packages`, `Python 3.14.8`;
     - `System check identified no issues (0 silenced).`, migrations ending `sessions.0001_initial... OK`;
     - `1160 passed in 124.22s`, with the test database created by the `CREATEDB` role;
     - both seed lines, and `Password set for demo-approver, demo-production, demo-quality, demo-warehouse`;
     - `login page: 200` and `login POST: 302`;
     - both `grep -F` lines matched, including `<tr><td>LED-CHIP</td><td>L-0001</td><td>RM-A</td><td class="text-end">100</td><td>RELEASED</td></tr>`;
     - the seed rerun gave an empty `diff counts-before.txt counts-after.txt` (`auth.User 4`, `inventory.StockLedgerEntry 37`);
     - the reset printed both seed lines and the password line again.
   - **Why the checks are meaningful:** a failed login returns 200 and a CSRF failure returns 403, so `302` really proves the login. The `pgrep` check proves the server stopped. If the server never starts, the wait loop runs out and the `code=$(curl …)` that follows fails under `bash -e`.

5. **Settings at the seam.**
   - `config/settings.py:13-17,70-74` reads `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` and `POSTGRES_*` only.
   - The job sets no `POSTGRES_*` or `DJANGO_*` variable, so the app reads only the `.env` that the guide writes.
   - `.env.example` has the four lines the `sed` rewrites (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`).
   - `DJANGO_DEBUG=true` on the command line wins over `.env`'s `false`. The CI log confirms this: the server served pages under the default `ALLOWED_HOSTS`.
   - The exported `PG*` variables do not leak into the app, because Django passes the database parameters explicitly.

6. **"Who sees what" matches the code.**
   - The routes exist in `config/urls.py:8-42`.
   - Roles come from `demo/management/commands/seed_demo.py:79-82`, plus `seed_production_demo.py:58-62`, which grants APPROVER on LINE-1 and FG. That makes the guide's "APPROVER (RM-A, RM-B, LINE-1, FG)" correct.
   - Navigation rules are in `demo/permissions.py:14-41` (`can_move_stock`, `can_reverse`, `can_quality` and `order_actions` scrap/reverse).
   - The spec's HTTP status table agrees with these rules. I did not re-run the per-user HTTP table.

7. **`set_demo_passwords`.** `--password-stdin` exists and enforces `MIN_LENGTH` (`set_demo_passwords.py:17,30`). The guide states "at least 8 characters".

8. **Documentation.**
   - README "Run locally" is a summary with a link, and the old list is marked historical. README contains no commit SHA.
   - DEVELOPMENT.md "Local commands" links the guide, marks the PowerShell list historical (dated) and keeps Ruff. CI does run `ruff check` and `ruff format --check` (`foundation.yml:88,91`).
   - The walkthroughs' `set_demo_passwords` (interactive) does not conflict: the guide says it prompts without `--password-stdin`.
   - The Windows note says "ยังไม่ได้ทดสอบบน Windows".
   - All values are placeholders or `synthetic-ci-*`. I found no real secret.

9. **Relative links.** My own resolver over the 4 changed Markdown files reported only `docs/TASKS.md#สถานะปัจจุบัน`. That is a false positive from my slugger stripping Thai vowel marks: the heading `## สถานะปัจจุบัน` exists at `docs/TASKS.md:7`, and the link is on an unchanged line. **0 broken.**

10. **Commit coverage.**
    - `docs/INSTALL.md` is identical from `0fd26cc` to `2277b71` (`git diff --quiet`).
    - `1a4738e..2277b71` changes only the spec.
    - `.github/` has not changed since `5b022b4`.
    - So the development checks described in the spec still apply to the head.

11. **Not re-run by me.** I did not repeat the PostgreSQL 16 fresh-state development check, and I did not test the `sudo -u postgres` route or Windows. The CI log above is the evidence of record for the commands.

## Findings, most severe first

**1. Low–medium: the spec's status and CI citation are stale now that the PR is open.**
- **Where:** `docs/assignments/m72-install-guide.md:5` says "implemented on the branch; PR not opened; review: none." The Evidence section (line 174) says the CI result "is cited by link … once the PR is open". There is no such link yet.
- **Why it matters:** AGENTS.md makes the slice record hold the review status and a link to the PR's CI comment. Today the record says something that is no longer true. The PR body's "CI on PostgreSQL 18.6" box is also still unchecked, although run #286 passed.
- **Evidence:** PR #118 has been open since 10:14Z. The CI comment `issuecomment-6820950684` and job `131115776822` exist.
- **Smallest change:** in the same docs-only commit that adds `docs/reviews/m72-independent-review.md`:
  - mark the old status line historical (dated) and write "PR #118 open; independent review by a separate session: this report";
  - link the PR CI comment, **and** link the `install-guide` job or its PR check, because the CI comment does not cover that job;
  - tick the PR-body box.
  - This is not a CI-only commit, so AGENTS.md allows it.

**2. Low: one instruction in the guide was never checked.**
- **Where:** `docs/INSTALL.md:63-66` tells socket-only users to put `sudo -u postgres` in front of both `psql` commands and keep `PGHOST` and `PGPORT`.
- **Why it matters:** the spec's evidence covers the TCP superuser path only. The guide's claim that its commands were checked from a fresh state does not cover this route. It should work, because `sudo` resets the environment so `psql` uses the socket, and `$ERP_DB_PASSWORD` expands in the caller's shell. But it is unchecked.
- **Smallest change:** add "(this route was not checked)" to that sentence, or check it once and record the result in the spec.

**3. Low, structural follow-up rather than a blocker: nothing keeps the guide and the CI job identical in future.**
- **Where:** `foundation.yml:195-198` versus `docs/INSTALL.md`.
- **Why it matters:** a later edit to either file can drift, and CI stays green while the guide is wrong. The acceptance criterion only holds through reviewer diligence.
- **Evidence:** the 33 guide lines are duplicated by hand in the workflow. My extraction diff was a one-off.
- **Smallest change:** a follow-up issue for a small check in the `install-guide` job that diffs the guide's bash lines against the job's run lines, with an allow-list for the `# CI-only` lines. It is out of scope for M7.2 and needs owner approval.

**4. Low, wording: the guide reads the Version contract more strictly than it is written.**
- **Where:** `docs/INSTALL.md:17` ("uv at the version in the Version contract") and `:174` ("older than the Version contract").
- **Why it matters:** the contract says "uv 0.13.1 **in CI**" (`docs/DEVELOPMENT.md`, Version contract), not for local installs.
- **Smallest change:** either say "uv 0.13.1 (the version CI uses; see the Version contract)", or drop "in CI" from the contract in a separate change. A new pin needs its own reviewed change.

I found no defect in the CI job, in the guide's checked commands, in the claim that the existing jobs are unchanged, or in the README and DEVELOPMENT.md changes.

## Verdict

**fix-then-ship.** Every acceptance criterion I could check holds: the 18.6 CI job passes from a fresh state on the only allowed image, the commands match apart from the listed `# CI-only:` lines, the existing jobs are byte-identical, there are 0 broken links and no secrets. The biggest reason it is not a plain ship is finding 1: the slice record still says "PR not opened; review: none" and does not link the CI evidence. That is a docs-only fix in the same commit that adds this report. Findings 2 and 4 are one-line wording changes. Finding 3 is a follow-up for the owner to decide.

## Manager disposition (Manager session, repair round 1 of 2, documentation only)

Approved by the owner in chat on 2026-11-12. No change to `.github/workflows/foundation.yml` or to code.

| # | Disposition |
|---|---|
| 1 | Fixed: spec status (old line marked historical), links to the PR CI comment and to the `install-guide` job, with the note that the job's result is not in the CI comment by design; the PR-body CI box ticked. |
| 2 | Fixed (wording): `docs/INSTALL.md` marks the `sudo -u postgres` route "ยังไม่ได้ตรวจจริง" (not checked). |
| 3 | Not done in M7.2: follow-up [Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119), status "รอเจ้าของ จัดลำดับ"; no work started. |
| 4 | Fixed (wording): `docs/INSTALL.md` says uv 0.13.1 is the version CI uses, matching `docs/DEVELOPMENT.md:14` ("uv 0.13.1 in CI"); the Version contract is unchanged. |

The fixes in this round are documentation only; under AGENTS.md they need no new review.
