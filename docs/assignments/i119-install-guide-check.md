# Issue #119 — Keep `docs/INSTALL.md` and the `install-guide` CI job identical

Repository `porntaned/ERP-for-Factory`; branch `claude/vibrant-sagan-ivztik` (restarted from `main` `4f6c065` after
PR #120 merged); [Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119).
Status: **[PR #121](https://github.com/porntaned/ERP-for-Factory/pull/121) open, awaiting the owner; independent review by a
separate session: [ship](../reviews/i119-independent-review.md) (findings 1–5 await the owner's decision; no repair
made).** CI evidence of record: [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964)
(covers `postgresql-tdd`) and the `install-guide` check on the PR (first passing run: [job](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364021863/job/131684043453); not in
the CI comment by design). ("implemented on the branch; PR not opened; review: none" held until PR #121 was opened and
reviewed on 2026-11-13; before that "spec approved by the owner; implementation not started" — historical.)

Owner approval: [Issue #119 comment](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6842699856)
(2026-11-13) and the owner's chat message of the same day.

Roles (as they actually happen; updated as work proceeds):
- **Manager** = Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby`.
- **Implementer** = a sub-agent spawned by the Manager, started 2026-11-13. ("not started yet" held until
  2026-11-13 — historical.)
- **Reviewer** = a **separate Claude Code session**, given only the PR number, the Issue number and this path, as in
  M7.2. Not a sub-agent of the Manager. Report in `docs/reviews/i119-independent-review.md`.
- **Owner** decides the merge. No deployment. No session merges without the owner's explicit merge instruction for
  that PR.

## Purpose

M7.2 review finding 3: the commands of `docs/INSTALL.md` are copied by hand into the `install-guide` job of
`.github/workflows/foundation.yml`. They match today (apart from the `# CI-only:` differences), but only a reviewer's
comparison shows it; a later edit to either file can drift while CI stays green. This change makes CI fail when they
differ.

## Owner rulings (verbatim, Issue #119 comment 6842699856)

```text
- D1 = A แต่ step เช็กต้องอยู่ต่อจาก step "Guide 4: Get the code" (checkout) ทันที ไม่ใช่ step แรก
  เพราะก่อน checkout ยังไม่มีไฟล์ใน runner; script ต้องรันได้ทั้ง Python 3.12 (python3 ของ runner) และ 3.14
  และบรรทัดเรียก script เองต้องอยู่ใน allow-list
- D2 = (a) รายการบรรทัดแบบตรงตัวอักษร 2 ชุด
- D3 = อ่านแบบข้อความด้วย stdlib; หา job หรือ run: ไม่เจอต้องล้มชัด ๆ
- D4 = ข้ามบรรทัด # ฝั่ง CI; คู่มือห้ามมีบรรทัด # ใน bash block
แก้เกณฑ์ allow-list เป็น: ทุกรายการอ้างข้อใดข้อหนึ่งในรายการ CI-only ของ M7.2 (หรือบรรทัดเรียก script เอง)
และไม่มีรายการที่ไม่มีเหตุผล
ห้ามแตะ postgresql-tdd และ report, ห้ามเพิ่ม dependency, independent review โดย session แยก
```

## Scope

1. **`scripts/check_install_guide.py`** (standard library only; runs on Python 3.12 and 3.14):
   - Guide side: every line inside the ` ```bash ` blocks of `docs/INSTALL.md`, in order. A line starting with `#`
     inside a bash block is an error (D4).
   - CI side: every line of every `run:` of the job `install-guide` only, in step order, both `run: |` block scalars
     (indentation removed as GitHub does) and one-line `run:`. Lines starting with `#` (after leading spaces) are
     skipped (D4). Read as text with the standard library (D3); if the job `install-guide:` or any `run:` cannot be
     found, exit non-zero with a clear message — never pass silently.
   - Remove the allow-listed lines (below), then the two sequences must be **equal, character for character and in
     order**. On a difference: exit non-zero and print the first differing position with both sides.
   - On success: print a one-line summary (number of lines compared, number of allow-listed lines on each side).
2. **Allow-list (D2 = a): two lists of exact lines inside the script**, each entry with a comment naming its reason:
   - *Guide-only* (in the guide, not in CI): the seven `export` lines of guide step 2 (M7.2 CI-only item 2);
     `git clone https://github.com/porntaned/ERP-for-Factory.git` and `cd ERP-for-Factory` (item 4); the `runserver`
     line of guide step 8 (item 5).
   - *CI-only* (in CI, not in the guide): the background `runserver` line and the curl / grep / `pkill` / `pgrep`
     check lines of the "Guide 8" step (item 5); the lines of the step "CI-only: rerunning the seeds adds nothing"
     (item 6); `cat runserver.log || true` (item 7); and the line that runs this script (owner ruling D1).
   - **Every entry cites one item of the M7.2 `# CI-only:` list (or is the script's own call line); no entry without
     a reason.** Items 1 (setup-uv) and 3 (service superuser) change no `run:` line and need no entry.
   - Because the seed-rerun step repeats commands that also appear in guide step 7, a CI-only entry is matched
     together with the name of the step it belongs to (step name + exact line), so a repeated command is allowed only
     in that step. This keeps D2 (a) exact-line lists; the Implementer records how it was done.
3. **`.github/workflows/foundation.yml`**: one new step in the job `install-guide`, **immediately after the step
   "Guide 4: Get the code"** (checkout), marked `# CI-only:`, that runs the script with the runner's `python3`
   (3.12). Nothing else in the workflow changes: `postgresql-tdd` and `report` are byte-for-byte unchanged, and the
   existing steps of `install-guide` keep their commands.
4. **Tests `tests/ci/test_install_guide_check.py`** (no database), written **RED first** (the script does not exist →
   fail), then GREEN:
   - the real `docs/INSTALL.md` and `foundation.yml` pass;
   - the check **fails** when: (a) a guide command changes by one character; (b) a job command changes; (c) the job
     gets a line not in the allow-list; (d) a guide line is removed; (e) two lines swap order; (f) the `SQL` heredoc
     differs; (g) the guide has a `#` line in a bash block; (h) the job `install-guide` or its `run:` lines are
     missing; (i) a CI-only line appears in a step other than the one its entry names.
   The tests run in the full suite of `postgresql-tdd` and `install-guide` without changing `postgresql-tdd`.
5. **Docs**: one sentence in `docs/INSTALL.md` (prose, not inside a bash block) and in `docs/DEVELOPMENT.md` saying the
   match is checked automatically by `scripts/check_install_guide.py`; this spec's Evidence section.

## Not in scope

Changes to `postgresql-tdd` or `report`; any new dependency (including PyYAML; `pyproject.toml` and `uv.lock` stay
unchanged); changing the guide's commands or the existing `install-guide` steps; making CI extract and run the guide's
blocks itself; editing `AGENTS.md` (the `--depth=50` change goes in the post-merge docs PR); M7.3–M7.5; deployment.

## Acceptance criteria

- [x] Owner approval of scope and rulings D1–D4 (Issue #119 comment 6842699856).
- [ ] Tests written RED first, then GREEN; the failure cases (a)–(i) are proven, and the real files pass.
- [ ] Every allow-list entry cites an M7.2 `# CI-only:` item (or is the script's own call line); no entry without a
      reason.
- [ ] Standard library only; `pyproject.toml` and `uv.lock` unchanged; the script uses no syntax or stdlib API newer
      than Python 3.12. CI runs it with the runner's Python 3.12; the tests run it on 3.14.
- [ ] The new step sits immediately after "Guide 4: Get the code"; `postgresql-tdd` and `report` are byte-for-byte
      unchanged (checked with `cmp` as in M7.2); the other `install-guide` commands are unchanged.
- [ ] CI on PostgreSQL 18.6 passes all 3 jobs (CI comment link; the `install-guide` result by its job link).
- [ ] Relative links in changed Markdown files: 0 broken; `ruff check` and `ruff format --check` pass.
- [ ] Independent review by a separate session → `docs/reviews/i119-independent-review.md`; at most 2 repair rounds.
- [ ] Owner decides the merge; no deployment.

## Post-merge docs PR (owner, 2026-11-12, recorded in Issue #119)

Besides the usual TASKS.md / closeout updates, it records the PR #120 merge (`4f6c065`, main CI #291), removes the
"awaiting the owner's priority" contradiction in the M7.2 closeout, adds the "independent review by a sub-agent of the
Manager" wording to the `Type:` line of `docs/reviews/m61-pr2-independent-review.md`, and changes AGENTS.md Issue
workflow step 1 to option B (`git fetch origin '+refs/heads/*:refs/remotes/origin/*'`, keep the shallow check, old
text historical, owner chose B on 2026-11-12).

## Evidence

All runs below are **development checks** in the Implementer's session container (not CI). CI on PostgreSQL 18.6
is the evidence of record and is cited by the PR's CI comment once the PR is open. Synthetic values only
(`DJANGO_SECRET_KEY=synthetic-dev-check-only`, `POSTGRES_PASSWORD=synthetic-dev-only`).

### Commits (branch `claude/vibrant-sagan-ivztik`, base `main` `4f6c065`)

| Commit | What |
|---|---|
| `86732bd` | RED tests `tests/ci/test_install_guide_check.py` |
| `068d65f` | the one workflow step (still RED: the script does not exist yet) |
| `f87709b` | `scripts/check_install_guide.py` (GREEN) and one corrected test assertion (below) |
| `1a3cde7` | one prose sentence each in `docs/INSTALL.md` and `docs/DEVELOPMENT.md` |
| `820d9c7` | test (g) derives the INSTALL.md line number instead of hard-coding it (below) |

The workflow step was committed before the script because the script also fails on an allow-list entry that is
not used, and its own call line (owner ruling D1) exists only once the step is there.

### RED, then GREEN

| Run (development check) | Tree | Python | Result |
|---|---|---|---|
| `uv run pytest tests/ci/test_install_guide_check.py -q` | `86732bd` | 3.14.8 | **1 error** in collection: `FileNotFoundError: … scripts/check_install_guide.py` |
| `uv run pytest tests/ci -q` | uncommitted, before `f87709b` | 3.14.8 | 1 failed, 26 passed: `test_real_job_is_read_step_by_step` |
| `uv run pytest tests/ci -q` | `f87709b` | 3.14.8 | **27 passed** (4 existing + 23 new) |
| `uv run pytest tests/ci -q` | `1a3cde7` | 3.14.8 | 2 failed, 25 passed: both `test_g_…` cases |
| `uv run pytest tests/ci -q` | `820d9c7` | 3.14.8 | **27 passed** |
| `uv run pytest -q` (full suite, PostgreSQL **16.15**, throwaway cluster on port 55432, deleted afterwards) | `f87709b` | 3.14.8 | **1183 passed** in 229.86s |
| same | `820d9c7` | 3.14.8 | **1183 passed** in 242.81s |

The two failures after RED were test defects, not script defects: the first assertion expected `job_steps()` to
drop `#` lines, but by design `ci_lines()` drops them (D4; the test now checks both); the second hard-coded
"line 27", which the prose sentence of `1a3cde7` moved to line 29 (the test now computes the line).

The 23 new tests: the real files pass (explicit paths, and default paths from another working directory); the
real job is read step by step (one-line `run:`, continuation lines keep their own indentation, `# CI-only:` lines
are read then skipped, `postgresql-tdd` lines are not read); the guide side is only the bash blocks; every
allow-list entry has an allowed reason and names a real step; and the failure cases, each from the real files
with a small text edit in a tmp file, run through `main()` (exit 1, `FAILED`, both lines shown):
(a) `uv sync --locked --all-groups` → `--all-group` in the guide; (b) `migrate` → `migrat` in the job; (c) an extra
`flush --noinput` line in the job; (d) `uv run python --version` removed from the guide, and the last guide line
removed (`(end of the guide's commands)`); (e) `check` and `migrate` swapped; (f) the `CREATE DATABASE` heredoc line
changed, once in the guide and once in the job; (g) `# check the tools`, at column 0 and indented, in a guide bash
block; (h) the job renamed, a job without `steps:`, a job without any `run:`, an empty `run: |`, and an unsupported
`run: >-`; (i) `pkill -f 'manage.py runserver'` added to "Guide 9", and the seed-rerun step renamed; plus an unused
allow-list entry (`cd ERP-for-Factory` removed from the guide).

Mutation check (development check, uncommitted script before `f87709b`, which differs only in not catching
`UnicodeDecodeError`; restored afterwards and checked with `cmp`): matching CI-only entries by
line only, ignoring the step name, makes 6 tests fail, including both (i) cases and the real files (the seed lines
of "Guide 7" are then removed too).

Real files, `python3 scripts/check_install_guide.py` (`820d9c7`):

```text
install guide check OK: 23 commands match in order (allow-listed: 10 guide-only lines, 25 CI-only lines)
```

The guide has 33 bash-block lines (10 guide-only); the job has 48 compared `run:` lines (25 CI-only); 23 remain on
each side and are equal in order. The bash-block lines of `docs/INSTALL.md` are identical to `main` `4f6c065`
(33 lines, compared with the script's own `guide_lines()`).

### Allow-list and reasons

Every entry is a dict key in the script with its reason as the value, under a comment naming the M7.2 item; a test
checks the reasons. Items 1 (setup-uv) and 3 (service superuser) change no `run:` line and have no entry.

| Side | Entries | Reason |
|---|---|---|
| guide-only | the 7 `export` lines of guide step 2 | M7.2 CI-only item 2 (job `env`) |
| guide-only | `git clone https://github.com/porntaned/ERP-for-Factory.git`, `cd ERP-for-Factory` | M7.2 CI-only item 4 (`actions/checkout`) |
| guide-only | `DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver` | M7.2 CI-only item 5 |
| CI-only, step "Guide 8: Run and log in" | 16 lines: background `runserver … > runserver.log 2>&1 &`; the wait loop; login page `code=…`/`echo … test … 200`; GET with cookies; `csrf=$(awk …)`; the 3 physical lines of the login POST; `echo … test … 302`; GET balance; the 2 `grep -F` lines; `pkill`; `sleep 2`; `if pgrep …` | M7.2 CI-only item 5 |
| CI-only, step "CI-only: rerunning the seeds adds nothing" | 7 lines: `count=…`, counts before, `seed_demo`, `seed_production_demo`, counts after, `cat counts-after.txt`, `diff …` | M7.2 CI-only item 6 |
| CI-only, step "CI-only: runserver log" | `cat runserver.log \|\| true` | M7.2 CI-only item 7 |
| CI-only, step "CI-only: guide and job commands match" | `python3 scripts/check_install_guide.py` | owner ruling D1 |

**Step scoping:** `CI_ONLY` is a dict keyed by `(step name, exact line)`; the CI side is a list of
`(step name, line)` pairs, and a pair is removed only if that exact pair is a key. So `seed_demo` and
`seed_production_demo` are allowed only in the seed-rerun step; the same lines in "Guide 7" stay in the comparison.
`GUIDE_ONLY` is keyed by exact line (the guide has no steps in this sense). After the comparison, any entry that
matched nothing fails the check ("allow-list entries not used"), so the lists cannot go stale. This check is not
written in the spec; it was added so that every entry stays tied to a line that exists.

**How the workflow is read** (text only, standard library): the job `install-guide:` is found at the indentation
of the first key under top-level `jobs:`; its `steps:`; each `- ` item at the steps' indentation is one step; at
the step's key indentation, `name:` (quotes removed) and `run:`. `run: |` is read as a block scalar: indentation of
the first non-blank line removed, a less indented line ends it, trailing blank lines dropped (clip). A one-line
`run:` is taken as is. Any other form (`|-`, `>-`, quoted, anchors, ` #` in the value) or an empty block fails with
the step name. Missing `jobs:`, job, `steps:` or any `run:` fails with a message. Unreadable or non-UTF-8 files fail
with `FAILED` and exit 1.

### Existing jobs unchanged

Development check on `068d65f` and again on `820d9c7` (the workflow does not change after `068d65f`), against
`git show 4f6c065:.github/workflows/foundation.yml`:

- `git diff --numstat 4f6c065 -- .github/workflows/foundation.yml` → `5 0`; one hunk `@@ -254,0 +255,5 @@`,
  0 removed lines.
- The line `  install-guide:` starts at byte 7436 in both files; `head -c 7436` of both are equal (`cmp`), so
  `postgresql-tdd` and `report` (and the comment before `install-guide`, from byte 7071) are byte-for-byte unchanged.
- Lines 1–254 are equal (`head -n 254 | cmp`), and `main` lines 255–end equal new lines 260–end (`tail -n | cmp`):
  the only change is the 5 added lines (comment, blank, step) right after the `Guide 4: Get the code` step.

### Python 3.12 compatibility

- `/usr/bin/python3.12` (**Python 3.12.3**) is present in the container; no download was needed.
- `python3.12 -I -X dev -W error scripts/check_install_guide.py` → the OK line above, exit 0 (`820d9c7`).
- `uv run --no-project --isolated --python /usr/bin/python3.12 --with pytest==9.1.1 python -X dev -m pytest -q
  -p no:cacheprovider tests/ci/test_install_guide_check.py` → **23 passed** (`820d9c7`; pytest only, no
  pytest-django, hence one `Unknown config option: DJANGO_SETTINGS_MODULE` warning). Every failure case (a)–(i)
  therefore also runs on 3.12.
- The script also passes on Python 3.13.18 (`python3 -I -X dev`) and 3.14.8 (`uv run python -X dev`).
- Manual review: imports only `argparse`, `sys`, `pathlib`; no PEP 695 `type`, no 3.13+ API. `python3.11 -m
  py_compile` also succeeds.
- CI runs it with the runner's `python3` (3.12); that run is the evidence of record.

### Other checks (development checks, `820d9c7`)

- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `277 files already formatted`.
- `git diff --check 4f6c065` → no output.
- Relative links in `docs/INSTALL.md`, `docs/DEVELOPMENT.md` and this file: 13 checked, **0 broken** (file and
  heading anchors).
- `git diff --quiet 4f6c065 -- pyproject.toml uv.lock AGENTS.md docs/MULTI_AGENT.md docs/TASKS.md` → exit 0
  (unchanged); no new dependency.

### Review

None yet. The independent review by a separate session goes in `docs/reviews/i119-independent-review.md`.
