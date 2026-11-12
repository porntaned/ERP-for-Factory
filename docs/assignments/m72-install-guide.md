# M7.2 — Install guide checked from a fresh state

Repository `porntaned/ERP-for-Factory`; branch `claude/vibrant-sagan-ivztik` (restarted from `main` `1261e86`
after PR #116 merged); [Issue #117](https://github.com/porntaned/ERP-for-Factory/issues/117).
Status: **merged: [PR #118](https://github.com/porntaned/ERP-for-Factory/pull/118) at `86ff46a` (2026-11-12); M7.2 complete**
("PR #118 open, awaiting the owner; independent review … fix-then-ship, repair round 1 of 2 done" held until the merge —
historical).
("implemented on the branch; PR not opened; review: none" held until PR #118 was opened and reviewed on
2026-11-12 — historical; before that "spec approved by the owner; implementation not started" — historical.)

CI evidence of record (PostgreSQL 18.6): [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/118#issuecomment-6820950684)
(always shows the latest head; it covers `postgresql-tdd` only) and the
[`install-guide` job](https://github.com/porntaned/ERP-for-Factory/actions/runs/43198580663/job/131115776822), whose result
**is not in the CI comment by design** (`report` needs only `postgresql-tdd`); on later heads see the `install-guide`
check on the PR. Follow-up for review finding 3: [Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119)
("รอเจ้าของ จัดลำดับ", not started).

Owner approval: [Issue #117 comment](https://github.com/porntaned/ERP-for-Factory/issues/117#issuecomment-6820317207)
(2026-11-12) and the owner's chat message of the same day (conditions 1–5 below).

Roles (as they actually happen; updated as work proceeds):
- **Manager** = Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby` (the owner's chat session for this period).
- **Implementer** = a sub-agent spawned by the Manager (started 2026-11-12).
- **Reviewer** = a **separate Claude Code session**, given only the PR number, the Issue number and this path,
  as in M6.2–M6.4. Not a sub-agent of the Manager. Report in `docs/reviews/m72-independent-review.md`.
  Performed by session `session_01MVmjhffM5mrrwnjZ2VDjRz` (created by the Manager), on head `2277b71`, 2026-11-12.
- **Owner** decides the merge. No deployment.

**Merge rule as it stands.** `AGENTS.md:5` and `:20` on `main` still say the owner merges ("The owner reviews and
merges changes"; "never ... merge ... automatically"). In practice the owner has had sessions merge on an explicit
merge instruction (e.g. PR #116). That practice — *a session merges only on the owner's explicit instruction, quoted
in the record* — is **how work is done now, not yet a written rule**; it becomes the rule only after post-merge
item (c) is merged. Until then **no session merges anything without an explicit merge instruction from the owner
for that round**.

## Purpose

A visitor who clones the repository should get from nothing to the running demo by following one page, and
the project should prove that page works from a fresh state. Today the steps are split and disagree:

- `README.md` "Run locally" (bash): `cp .env.example .env`, `uv sync`, `migrate`, `pytest`, `seed_demo`,
  `set_demo_passwords`, `runserver`; no `seed_production_demo`.
- `docs/DEVELOPMENT.md` "Local commands" (PowerShell): `Copy-Item`, `uv sync`, `check`, `pytest`, `ruff`; no
  `migrate` or seeds.
- Neither says the PostgreSQL user must be able to create the test database (pytest-django creates
  `test_<POSTGRES_DB>`), nor how to create the role and database.
- Nobody has recorded running the steps from a fresh clone and an empty database.

## Owner rulings (verbatim, Issue #117 comment 6820317207)

```text
- D1 = C (CI job ใหม่แยกจาก job เดิม บน PostgreSQL 18.6 เป็นหลักฐานหลัก; ผลใน container เป็น development check)
- D2 = bash เป็นหลัก หมายเหตุ Windows ต้องเขียนว่า "ยังไม่ได้ทดสอบบน Windows"
- D3 = ไม่มี Docker/compose
- Independent review โดย session แยก
- คำสั่งใน CI job ต้องตรงกับ INSTALL.md ตามตัวอักษร
- README, DEVELOPMENT.md และ INSTALL.md ต้องไม่มีคำสั่งที่ขัดกัน และลิงก์ relative เสีย 0
- ห้ามแก้ AGENTS.md ใน M7.2
```

Further conditions from the owner's chat (2026-11-12), summarised:

1. D1: the new CI job is **separate** from `postgresql-tdd`; **the existing jobs are not changed**. Results in the
   session container (PostgreSQL 16) are labelled a development check.
2. D3: no Docker/compose and no pulling of outside images by this work.
3. Review by a separate session (PR number, Issue number, spec path only); never a Manager sub-agent.
4. The `--depth=50` finding about AGENTS.md step 1 is reported to the owner; AGENTS.md is not edited in M7.2.
5. Post-merge docs PR item (e) is added (below).

**Owner ruling on the CI image (2026-11-12, chat):** the new CI job may use the service image
`postgres:18.6-bookworm`, the same image as `postgresql-tdd`; **no other image**. (The statements of this in Scope
item 4 and in the D3 parenthesis of Issue #117 were written by the Manager before the owner confirmed it; the owner
confirmed it on 2026-11-12.)

Further item (f) for the post-merge docs PR was added by the owner in chat on 2026-11-12 (below).

## Scope

1. **`docs/INSTALL.md`** (new), the single install guide, bash first:
   - What you need, pointing to the Version contract in `docs/DEVELOPMENT.md` (no second copy of the pins):
     Git, uv, Python 3.14.8 (installed by uv), PostgreSQL 18.6 installed any way (link to the official download
     page; no Docker/compose instructions).
   - Create the role and database with `psql` as a PostgreSQL superuser, with synthetic placeholder values; the
     role gets `CREATEDB` so pytest-django can create the test database. Explain why in one line.
   - `git clone` → `.env` from `.env.example` (every placeholder replaced; how, without real secrets) →
     `uv sync --locked --all-groups` → `manage.py check` → `migrate` → `pytest` → `seed_demo` →
     `seed_production_demo` → `set_demo_passwords` → `runserver` → log in.
   - Which demo user sees which screen (only screens that exist in `config/urls.py`), and links to the existing
     walkthroughs in `docs/DEVELOPMENT.md` instead of copying them.
   - Reset: `seed_demo --reset` / `seed_production_demo --reset` flush every table; disposable databases only.
   - Troubleshooting: only problems actually met while checking the guide (with the real error text).
   - A Windows note that states **"ยังไม่ได้ทดสอบบน Windows"** (not tested on Windows).
2. **`README.md`** "Run locally": a short summary and a link to `docs/INSTALL.md`; no commit SHA.
3. **`docs/DEVELOPMENT.md`** "Local commands": point to `docs/INSTALL.md`; keep only developer-only commands
   (Ruff, format) that the guide does not cover. Statements that no longer hold are marked historical, not deleted.
4. **`.github/workflows/foundation.yml`**: one **new job** (for example `install-guide`) that follows
   `docs/INSTALL.md` on `ubuntu-24.04` with PostgreSQL 18.6. The jobs `postgresql-tdd` and `report` are not edited.
   - It uses the same service image already used by `postgresql-tdd` (`postgres:18.6-bookworm`); no other image.
     (Written before the owner confirmed it; owner ruling 2026-11-12 above.)
     The service starts with only a superuser, so the job runs the guide's own role/database `psql` commands.
   - Every command in the guide's checked path appears in the job **in the same order and character for
     character**. The only allowed differences, each marked in the workflow with a `# CI-only:` comment and listed
     in this spec's Evidence section:
     - `git clone` is replaced by `actions/checkout`; installing uv is replaced by the pinned setup-uv action;
     - values the guide tells the reader to choose (passwords, secret key) come from job env variables named in
       the guide;
     - `runserver` is started in the background, followed by HTTP checks (login page 200; log in as a demo user;
       the balance page shows the seeded stock) and then stopped;
     - re-running the seed commands to show they add nothing.
   - The new job does not feed the CI comment (the `report` job and `scripts/ci_summary.py` stay unchanged); its
     result is the job's own status on the PR and on `main`.
5. **`docs/assignments/m72-install-guide.md`** (this file): Evidence section with the fresh-state run.

## Not in scope

Deploy/hosting; Docker, compose, pulled images or any new dependency; application code or settings; changes to
`postgresql-tdd` or `report`; M7.3–M7.5; testing on Windows or macOS; production hardening; deleting or archiving
branches; editing `AGENTS.md` or `docs/MULTI_AGENT.md`.

## Acceptance criteria

- [ ] Spec and rulings D1–D3 approved by the owner before writing (done: comment 6820317207).
- [ ] Every command in `docs/INSTALL.md` was run, in order, from a fresh clone and an empty PostgreSQL database;
      results recorded here with the commit they ran on. The session-container run (PostgreSQL 16) is labelled a
      development check.
- [ ] Results seen: `check` passes, `migrate` passes, the full suite passes, both seeds run and a second run adds
      nothing, the login page answers 200, and a logged-in demo user sees the seeded stock (exact text recorded).
- [ ] The new CI job passes on PostgreSQL 18.6; `postgresql-tdd` and `report` are byte-for-byte unchanged and still
      pass.
- [ ] **The commands in the new CI job match `docs/INSTALL.md` character for character**, apart from the listed
      `# CI-only:` differences. The reviewer compares them line by line.
- [ ] `README.md`, `docs/DEVELOPMENT.md` and `docs/INSTALL.md` contain no conflicting commands, and the relative
      links in every changed Markdown file resolve (**0 broken**).
- [ ] No real secrets: placeholders only; README has no commit SHA.
- [ ] Independent review by a separate session → `docs/reviews/m72-independent-review.md`; at most 2 repair rounds.
- [ ] CI evidence cited by link to the PR's CI comment while the PR is open; documentation in the same PR.

## Prohibited

Merging without the owner's explicit instruction; deployment; external services or images beyond the existing CI
service image; new dependencies; force-push; editing `AGENTS.md` / `docs/MULTI_AGENT.md`; real data or secrets.

## Post-merge docs PR (owner, 2026-11-12)

The Manager opens it immediately after the owner merges M7.2. It also does:

- (a) record the merge of PR #116 at `1261e86`, merged by `session_01MVmjhdAZRZbr6kL22x7hby` on the owner's
  instruction (quoted verbatim in Issue #117), with PR CI #284 and main CI #285
  ([CI comment](https://github.com/porntaned/ERP-for-Factory/commit/1261e86a5dbd396dd9f10234e44e353829cebcc6#commitcomment-209414826),
  1160 passed);
- (b) `docs/assignments/docs-repair-2026-11-11.md`: "PR open, awaiting the owner" → historical; closeout with merge
  SHA, PR CI #284 and main CI #285;
- (c) `AGENTS.md:5` and `:20` describe what happens: the owner decides; a session merges only on the owner's explicit
  instruction, and that instruction is quoted in the record (current practice; it is the rule only once this item is
  merged — see "Merge rule as it stands" above);
- (d) a `Type:` line at the top of `docs/reviews/m61-pr2-independent-review.md` saying it was a sub-agent of the
  Manager, with the date of the correction;
- (e) if the owner has created the archive tags and deleted the branches by then:
  `docs/reviews/project-audit-after-pr12.md:3` "not done yet" → historical, with the tag name and the date;
- (f) `AGENTS.md` Issue workflow step 1: check `git rev-parse --is-shallow-repository`; if it prints `true`, run
  `git fetch --unshallow origin` before trusting `git branch -r --no-merged`. Attach the commands and results below.

  Observed in this session's clone on 2026-11-12 (after `main` moved from `217be3f` to `1261e86`):

  ```bash
  git fetch --depth=50 origin '+refs/heads/*:refs/remotes/origin/*'
  for b in $(git branch -r | grep -v HEAD); do if ! git merge-base --is-ancestor $b origin/main 2>/dev/null; then echo "UNMERGED: $b"; fi; done
  ```

  | Step | `git rev-parse --is-shallow-repository` | Branches reported unmerged |
  |---|---|---|
  | First run at session start (2026-11-11) | not checked | 5 |
  | Same commands after `main` moved to `1261e86` | `true` (`.git/shallow` had 2 lines; all 31 gave exit code 1) | **31** (false) |
  | After `git fetch --unshallow origin` and the same fetch again | `false` | **5** (correct) |

  Re-tried in the scratchpad: a full `git clone` and a `git clone --depth=50`, each followed by the AGENTS.md fetch,
  both reported 5 and ended non-shallow. So the 31 came from this clone's shallow state; the check of
  `--is-shallow-repository` is what guards against it.

## Evidence

### Fresh-state run — development check (PostgreSQL 16, session container) — not evidence of record; CI on PostgreSQL 18.6 is

Run by the Implementer (a sub-agent of the Manager) on 2026-11-12. Self-verification, not a review. The CI
result of the `install-guide` job is cited at the top of this file (Status). ("is cited by link … once the PR is
open" held until PR #118 was opened — historical, 2026-11-12.)

**Environment:** Ubuntu 24.04.5 LTS (session container, kernel 6.18.44); PostgreSQL **16.15**
(Ubuntu 16.15-0ubuntu0.24.04.1), a throwaway cluster made with `initdb` (superuser `postgres`, synthetic password,
scram-sha-256, TCP 127.0.0.1:55432 only), empty except `postgres`/`template0`/`template1`, no `erp_factory` role;
uv **0.13.1** (installed from PyPI into the scratchpad, see problem 1); Python **3.14.8** (installed by the guide's
`uv python install 3.14.8`); git 2.43.0; curl 8.5.0; Django 5.2.18, pytest 9.1.1, pytest-django 4.14.0 (from
`uv.lock`). Each run started from a new directory with a new `git clone` of the branch's committed state from the
local repository and an empty database (role and databases dropped before the run).

**Run 2 — the guide's commands, in order, literally** (every ` ```bash ` block of `docs/INSTALL.md` extracted by a
script and run with `set -euo pipefail`). Commit **`0fd26cc`** (clone printed
`commit 0fd26cc642537ec9d5da02f396653d51cefd53a0`); `docs/INSTALL.md` is byte-identical at `1a4738e`
(`git diff --quiet 0fd26cc 1a4738e -- docs/INSTALL.md`). Only these substitutions, the first four being the values
the guide tells the reader to choose:
`PGPORT=55432`, `PGPASSWORD`/`ERP_DB_PASSWORD`/`ERP_DEMO_PASSWORD` set to synthetic values
(`ERP_SECRET_KEY` from the guide's own `openssl rand -hex 32`); `git clone --branch claude/vibrant-sagan-ivztik
/home/user/ERP-for-Factory ERP-for-Factory` instead of the GitHub URL (the branch's new commits were not pushed);
`runserver` in the background with HTTP checks instead of a browser, then stopped.

| Guide step / command | Result |
|---|---|
| `git --version`; `uv --version` | `git version 2.43.0`; `uv 0.13.1 (x86_64-unknown-linux-gnu)` |
| `psql -d postgres -tAc 'SHOW server_version'` | `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)` |
| `psql -v ON_ERROR_STOP=1 -v db_password=… -d postgres <<'SQL' …` | `CREATE ROLE`, `CREATE DATABASE` |
| `git clone …`; `cd ERP-for-Factory`; `sed … .env.example > .env` | clone done; `.env` written (no `replace-with` left) |
| `uv python install 3.14.8` | `Installed Python 3.14.8` |
| `uv sync --locked --all-groups` | `Installed 12 packages` (django 5.2.18, psycopg 3.3.6, pytest 9.1.1, pytest-django 4.14.0, ruff 0.17.1, …) |
| `uv run python --version` | `Python 3.14.8` |
| `… manage.py check` | `System check identified no issues (0 silenced).` |
| `… manage.py migrate` | every migration `OK` (last `sessions.0001_initial`) |
| `uv run --env-file .env pytest` | **`1160 passed in 273.49s`** (test database `test_erp_factory` created by the role through `CREATEDB`) |
| `… seed_demo` | `Seeded LEDCO/P1: RM-A, RM-B, LINE-1, FG; lot L-0001 received 100 at RM-A and RELEASED; BOM LAMP-A19 v1 ACTIVE.` |
| `… seed_production_demo` | the line above, then `Seeded M5.4 production demo: order 1 LAMP-A19 x 10 CLOSED, net output 9 (LAMP-0001 5, LAMP-0002 4 at FG, HOLD); shortfall reason recorded. M6.3 chain: L-0004 -> LED-BOARD-0001 -> LAMP-BR30-0001 (FG, HOLD).` |
| `printf … \| … set_demo_passwords --password-stdin` | `Password set for demo-approver, demo-production, demo-quality, demo-warehouse` |
| `DJANGO_DEBUG=true … runserver` (background) | login page **200**; login POST as `demo-warehouse` with CSRF **302**; `/` **200**, nav shows `demo-warehouse` and the row `<tr><td>LED-CHIP</td><td>L-0001</td><td>RM-A</td><td class="text-end">100</td><td>RELEASED</td></tr>`; server stopped (`pgrep` empty) |
| Seeds run again (check, not a guide command) | per-model row counts before and after identical (`diff` empty): 340 rows in all tables, `auth.User 4`, `inventory.StockLedgerEntry 37`, `quality.LotInspection 7`, `manufacturing.ProductionOrder 3` |
| `… seed_production_demo --reset`; `printf … \| … set_demo_passwords --password-stdin` | both seed lines again; `Password set for demo-approver, demo-production, demo-quality, demo-warehouse` |

Balance page rows seen after both seeds (Item Lot Warehouse Balance Quality): LED-CHIP L-0001 RM-A 100 RELEASED;
L-0002 RM-A 0 RELEASED; L-0002 LINE-1 0 HOLD; L-0003 RM-A 12 RELEASED; L-0003 LINE-1 0 HOLD; DRIVER D-0001 RM-A 11
RELEASED; D-0001 LINE-1 0 HOLD; LAMP-A19 LAMP-0001 FG 5 HOLD; LAMP-0002 FG 4 HOLD; LAMP-0003 FG 0 HOLD; LED-CHIP L-0004
RM-A 10 RELEASED; L-0004 LINE-1 0 HOLD; DRIVER D-0002 RM-A 5 RELEASED; D-0002 LINE-1 0 HOLD; LED-BOARD LED-BOARD-0001
LINE-1 0 HOLD; LED-BOARD-0001 FG 0 RELEASED; LAMP-BR30 LAMP-BR30-0001 FG 5 HOLD.

"Who sees what" in the guide, checked over HTTP after logging in as each user (status codes):

| User | `/` | `/receipts/new/` | `/transfers/new/` | `/history/` | `/production/` | `/production/new/` | `/lots/search/` | `/quality/` | `/quality/audit/` | `/admin/` |
|---|---|---|---|---|---|---|---|---|---|---|
| demo-warehouse | 200 | 200 | 200 | 200 | 200 | 403 | 200 | 403 | 403 | 302 (admin login) |
| demo-quality | 200 | 403 | 403 | 200 | 200 | 403 | 200 | 200 | 200 | 302 |
| demo-approver | 200 | 403 | 403 | 200 | 200 | 403 | 200 | 200 | 200 | 302 |
| demo-production | 200 | 403 | 403 | 200 | 200 | 200 | 200 | 403 | 403 | 302 |

The approver's reverse/Scrap buttons and the production record buttons were not clicked; the table states them from
`demo/permissions.py` (`order_actions`, `can_approve_all`) and the seeds' role assignments.

**Run 3 — the `install-guide` job's own `run:` lines**, on commit **`1a4738e`** (clone printed
`commit 1a4738e3641e24cd1ded0cbdfabee2ef3b1150d3`), new directory, empty database. A script turned the job into a
shell script: the job's `env` exported (with `PGPORT=55432` and the local superuser password instead of the
service's), `setup-uv` → the local uv 0.13.1, `actions/checkout` → the local clone, and every `run:` block verbatim
(the `if: failure()` log step skipped). Results: `16.15 …`, `CREATE ROLE`, `CREATE DATABASE`, `Python 3.14.8`,
`System check identified no issues (0 silenced).`, migrations `OK`, **`1160 passed in 261.26s`**, both seed lines,
`Password set for …`, `login page: 200`, `login POST: 302`, both `grep -F` lines matched, server stopped, seed rerun
`diff counts-before.txt counts-after.txt` empty, reset and passwords as in run 2; script exit 0.

**Problems met, and what changed:**
1. uv 0.11.32 (the container's uv) cannot install the pinned Python: `uv python install 3.14.8` →
   `error: No download found for request: cpython-3.14.8-linux-x86_64-gnu`. Added to the guide's Troubleshooting;
   the guide already requires the uv of the Version contract. The uv installer host (`astral.sh`) and GitHub release
   downloads are refused by this container's network proxy (`curl: (56) CONNECT tunnel failed, response 403`), so uv
   0.13.1 came from PyPI into the scratchpad. A container limit, not a guide problem; not in the guide.
2. Run 1 stopped at a bug in my own run script (`git log` before `cd`), not in the guide; re-run from scratch as run 2.
3. The throwaway cluster could not live under the scratchpad: the Unix socket path there is over 107 bytes, and the
   session tool resets the scratchpad root to mode 700, so the server lost access to its data directory
   (`PANIC:  could not open file ".../global/pg_control": Permission denied`). The cluster was re-made in
   `/var/tmp/claude-m72-pg` with TCP only; container-specific, not in the guide.
No command of `docs/INSTALL.md` had to change.

**`# CI-only:` differences** (the only differences between the guide's commands and the job; computed by a script that
diffs the guide's ` ```bash ` lines against the job's steps — nothing else differs):
1. `astral-sh/setup-uv` (existing pin `1c37ad0…`, v10.3.0, uv 0.13.1; no cache, since the checkout comes later)
   replaces installing uv by hand (guide step 1).
2. The job `env` (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `ERP_DB_PASSWORD`, `ERP_SECRET_KEY`,
   `ERP_DEMO_PASSWORD`, synthetic) replaces the seven `export` lines of guide step 2. No `POSTGRES_*` or `DJANGO_*`
   variable is set in the job, so the app reads its settings only from the `.env` the guide writes.
3. The service `postgres:18.6-bookworm` starts with only the superuser (`POSTGRES_USER: postgres`); the guide's
   step 3 creates the role and the database.
4. `actions/checkout` (existing pin `3d3c42e…`, v7.0.1) replaces `git clone https://github.com/porntaned/ERP-for-Factory.git`
   and `cd ERP-for-Factory`, at the same place in the order (after step 3).
5. `runserver` runs with `> runserver.log 2>&1 &`, followed by curl checks (wait; login page 200; GET + POST login as
   `demo-warehouse` with the CSRF cookie → 302; the balance page contains the nav `demo-warehouse` and the L-0001 row
   above) and `pkill`, then a check that it stopped.
6. An extra step reruns `seed_demo` and `seed_production_demo` and diffs per-model row counts before and after.
7. An extra `if: failure()` step prints `runserver.log`.

**Existing jobs unchanged:** the first 7070 bytes of the new `foundation.yml` equal the whole file at `main` `1261e86`
(`head -c 7070 … | cmp`), the diff has 0 removed lines and one hunk `@@ -192,3 +192,133 @@` appended after the last
line; parsed with PyYAML 6.0.3 (system Python, no new dependency), `postgresql-tdd`, `report` and the top-level keys
are equal to `main`'s, and `report` still `needs: postgresql-tdd` only. `scripts/ci_summary.py` is not changed or used
by the new job.

**Other checks** (on the working tree of `5b022b4`, then re-run before the Evidence commit): `uv run ruff check .` →
`All checks passed!`; `uv run ruff format --check .` → `273 files already formatted`; `git diff --check` → clean.

**Relative links** in every changed Markdown file (`README.md`, `docs/DEVELOPMENT.md`, `docs/INSTALL.md`, this file),
checked by a script that resolves each relative path and its `#anchor` against the target's headings: **21 links,
0 broken** (the checker reported 2 of 3 deliberately broken links in a negative test).

**No conflicting commands** between `README.md`, `docs/DEVELOPMENT.md` and `docs/INSTALL.md`:
- Setup (`psql` role/database, `git clone`, `.env` via `sed`, `uv python install 3.14.8`, `uv sync --locked
  --all-groups`, `check`, `migrate`, `pytest`, both seeds, `set_demo_passwords --password-stdin`, `runserver`,
  `--reset`): only in `docs/INSTALL.md` as commands. `README.md` "Run locally" names the steps in prose and links the
  guide; `docs/DEVELOPMENT.md` "Local commands" links the guide and marks its former PowerShell list historical.
- `uv run ruff check .` / `uv run ruff format --check .` / `uv run ruff format .`: only in `docs/DEVELOPMENT.md`
  ("Local commands", and the Evidence rule line).
- The walkthroughs in `docs/DEVELOPMENT.md` (M4.7–M6.4) keep their own `migrate`, `seed_* --reset`,
  `set_demo_passwords` (interactive prompt) and `runserver` lines; they are the same commands as the guide's (same
  `uv run --env-file .env python manage.py …` form; the guide states the prompt is used without `--password-stdin`).

## Closeout (2026-11-12)

[PR #118](https://github.com/porntaned/ERP-for-Factory/pull/118) was merged on GitHub at 2026-11-12T14:35:40Z as merge commit
`86ff46ae8221d46f6d65d00d2d9c91f67e614b08` (head `093aff0`) **by the owner on GitHub** (the owner confirmed this in chat on
2026-11-12). ("GitHub shows the owner's account … The Manager session did not merge it and received no merge instruction
for it" was written before the owner confirmed — historical.)
[PR CI #287](https://github.com/porntaned/ERP-for-Factory/actions/runs/43201621735) on `093aff0`: `postgresql-tdd` PostgreSQL 18.6 / Python 3.14.8 **1160 passed**
([CI comment](https://github.com/porntaned/ERP-for-Factory/pull/118#issuecomment-6820950684)), `install-guide` success, `report` success.
[Main CI #288](https://github.com/porntaned/ERP-for-Factory/actions/runs/43238815024) on `86ff46a`: all 3 jobs passed: `postgresql-tdd` PostgreSQL 18.6 / Python 3.14.8 **1160 passed**; `install-guide` success (PostgreSQL 18.6, 1160 passed, login page 200, login 302); `report` success ([CI comment](https://github.com/porntaned/ERP-for-Factory/commit/86ff46ae8221d46f6d65d00d2d9c91f67e614b08#commitcomment-209587321), 1160 passed).
Review stays: independent review by a separate session (`session_01MVmjhffM5mrrwnjZ2VDjRz`, head `2277b71`),
fix-then-ship; repair round 1 of 2 (`093aff0`) was documentation only and was not re-reviewed. Finding 3 is follow-up
[Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119) (awaiting the owner's priority). Post-merge items (a)–(d) and (f) are done in the post-merge
docs PR; so is (e): the owner created tags `archive/codex-project-audit-after-pr12` (`98103b2`) and
`archive/codex-inventory-concurrent-commands` (`3530bb6`) and deleted the five stale branches on 2026-11-12 ("(e) is not
done yet … the five branches are not deleted" held until then — historical). Issue #119 comes after this docs PR and
before M7.5; not started. No deployment.
