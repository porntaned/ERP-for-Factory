# Issue #119 — Keep `docs/INSTALL.md` and the `install-guide` CI job identical

Repository `porntaned/ERP-for-Factory`; branch `claude/vibrant-sagan-ivztik` (restarted from `main` `4f6c065` after
PR #120 merged); [Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119).
Status: **merged: [PR #121](https://github.com/porntaned/ERP-for-Factory/pull/121) at `6f6dd2b` (2026-11-14, by the owner on GitHub); Issue #119 complete** (see
[Closeout](#closeout-2026-11-15)). The status before the merge, kept as historical (held until the merge on 2026-11-14):

> Status: **[PR #121](https://github.com/porntaned/ERP-for-Factory/pull/121) open, awaiting the owner's merge (the owner merges on GitHub); [repair round 2](#repair-round-2-2026-11-14)
> (the final round: runserver stop fallback, owner [comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215)) done on the branch; independent review of the
> round-2 diff by a new separate session (`session_01MVmjhdTUAG56qPZmJnVeJn`): [ship](../reviews/i119-independent-review.md#re-review-2),
> its low/info findings recorded as known limits (owner rule 1) ("…review of the round-2 diff by a new separate session
> pending" held until that review on 2026-11-14 — historical). Merge criterion (owner): 3/3 checks pass on the PR page.** CI evidence
> of record: [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964) (covers `postgresql-tdd`; always shows the latest
> head; not changed for this round, owner) and the `install-guide` check on the PR (not in the CI comment by design).
> ("PR #121 open, awaiting the owner's merge; first review ship, re-review by a new separate session ship; re-review
> findings recorded as known limits and spec notes per the owner ([comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)), documentation only, no new
> review" held until `install-guide` failed in run #296 and the owner ordered repair round 2 on 2026-11-14; before
> that "repair round 1 done on the branch; re-review pending" held until the re-review and the owner's ruling on
> 2026-11-14; before that "PR #121 open, awaiting the owner; independent review by a separate session: ship (findings 1–5 await the owner's decision; no repair made)"
> held until repair round 1 on 2026-11-14; before that "implemented on the branch; PR not opened; review: none" until
> 2026-11-13; before that "spec approved by the owner; implementation not started" — historical.)

Owner approval: [Issue #119 comment](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6842699856)
(2026-11-13) and the owner's chat message of the same day.

Roles (as they actually happen; updated as work proceeds):
- **Manager** = Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby`.
- **Implementer** = a sub-agent spawned by the Manager, started 2026-11-13. ("not started yet" held until
  2026-11-13 — historical.) Repair round 1 (2026-11-14): a sub-agent spawned by the Manager. Repair round 2
  (2026-11-14): another sub-agent spawned by the Manager.
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
   existing steps of `install-guide` keep their commands. (Historical, 2026-11-14: one existing CI-only line changed —
   `sleep 2` in "Guide 8: Run and log in" became a wait loop of up to 20 s, finding 6 of repair round 1, owner
   [comment 6877846545](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6877846545); noted per [comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755).)
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
      unchanged (checked with `cmp` as in M7.2); the other `install-guide` commands are unchanged. (Historical,
      2026-11-14: except `sleep 2` in "Guide 8: Run and log in", replaced by a wait loop of up to 20 s — finding 6,
      owner comment 6877846545; noted per [comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755); and, in repair round 2, the stop check
      `if pgrep … "runserver still running"; exit 1; fi` of the same step, replaced by the `pkill -9` fallback —
      owner [comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215).)
- [ ] CI on PostgreSQL 18.6 passes all 3 jobs (CI comment link; the `install-guide` result by its job link). Merge
      criterion (owner, [comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215)): 3/3 checks pass on the PR page; the CI comment is not changed.
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
| CI-only, step "Guide 8: Run and log in" | 22 lines: background `runserver … > runserver.log 2>&1 &`; the wait loop; login page `code=…`/`echo … test … 200`; GET with cookies; `csrf=$(awk …)`; the 3 physical lines of the login POST; `echo … test … 302`; GET balance; the 2 `grep -F` lines; `pkill`; the stop loop `for i in $(seq 1 20); do pgrep …` (`sleep 2` until repair round 1, 2026-11-14 — historical); the 7 lines of the `pkill -9` fallback, `if pids=$(pgrep -d, …); then` … `fi` (see [Repair round 2](#repair-round-2-2026-11-14); "16 lines" ending with `if pgrep … "runserver still running"; exit 1; fi` held until repair round 2, 2026-11-14 — historical) | M7.2 CI-only item 5 |
| CI-only, step "CI-only: rerunning the seeds adds nothing" | 7 lines: `count=…`, counts before, `seed_demo`, `seed_production_demo`, counts after, `cat counts-after.txt`, `diff …` | M7.2 CI-only item 6 |
| CI-only, step "CI-only: runserver log" | `cat runserver.log \|\| true` | M7.2 CI-only item 7 |
| CI-only, step "CI-only: guide and job commands match" | `python3 scripts/check_install_guide.py` | owner ruling D1 |

**Step scoping:** `CI_ONLY` is a dict keyed by `(step name, exact line)`; the CI side is a list of
`(step name, line)` pairs, and a pair is removed only if that exact pair is a key. So `seed_demo` and
`seed_production_demo` are allowed only in the seed-rerun step; the same lines in "Guide 7" stay in the comparison.
`GUIDE_ONLY` is keyed by exact line (the guide has no steps in this sense). After the comparison, any entry that
matched nothing fails the check ("allow-list entries not used"), so the lists cannot go stale. This check is not
written in the spec; it was added so that every entry stays tied to a line that exists. The owner kept it (finding 5,
[comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)). Since repair
round 1, each entry must also match exactly once, and each `GUIDE_ONLY` entry also names the compared command that must
come right after it (see [Repair round 1](#repair-round-1-2026-11-14)).

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

First independent review by a separate session (2026-11-13, head `aae03d8`): **ship**, with findings 1–6, in
[`docs/reviews/i119-independent-review.md`](../reviews/i119-independent-review.md). Re-review after repair round 1,
by a new separate session, not the first Reviewer (owner,
[comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)): **ship**, same
record. ("None yet" held until 2026-11-13; "pending" for the re-review until it reported on 2026-11-14 — historical.)
Review of the [repair round 2](#repair-round-2-2026-11-14) diff only: **pending**, by a new separate session, not
either earlier Reviewer (owner, [comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215)); the Manager records it in the review record.

### Repair round 1 (2026-11-14)

Done by a sub-agent spawned by the Manager (Implementer role), on `claude/vibrant-sagan-ivztik` from `6e4526c`. All
runs below are **development checks** in that sub-agent's container, not CI; CI on PostgreSQL 18.6 stays the evidence of
record ([the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964), latest
head).

**Owner rulings (verbatim).** [Issue #119 comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308) (2026-11-13):

```text
- Finding 1, 2, 3: แก้ในรอบแก้ที่ 1
  (1) ตรวจลำดับของบรรทัดที่มีแค่ในคู่มือด้วย
  (2) บรรทัด CI-only ต้องปรากฏพอดี 1 ครั้ง และชื่อ step ใน job install-guide ห้ามซ้ำ
  (3) ถ้า INSTALL.md มี code block แบบ sh หรือ shell ให้เช็กล้ม
- Finding 4: ไม่แก้ บันทึกเป็นข้อจำกัดใน spec และ review record
- Finding 5: คงไว้ (ล้มเมื่อมีรายการ allow-list ที่ไม่ได้ใช้) ผมยืนยัน
แก้แล้วต้องมี independent review รอบใหม่โดย session แยกตัวใหม่ (ไม่ใช่ Reviewer คนเดิม)
```

[Issue #119 comment 6877846545](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6877846545) (2026-11-14):

```text
เพิ่มคำตัดสิน finding 6 (runserver ปิดไม่ทันใน job install-guide, run #293 attempt 1):
แก้ในรอบแก้ที่ 1 พร้อม finding 1–3 โดยเปลี่ยน sleep 2 เป็น loop รอให้ process ปิดภายในเวลาที่กำหนด
(เป็นบรรทัด CI-only ห้ามแก้คำสั่งในคู่มือ) และอัปเดต allow-list ให้ตรง
```

The owner's chat of 2026-11-14 (as relayed by the Manager) asked for RED tests first, then GREEN, for findings 1–3,
covering a guide-only line moved to a wrong position, a CI-only line duplicated, a duplicate step name and a `sh` /
`shell` block in INSTALL.md.

"Finding 6" in the owner's second comment is the runserver stop failure of
[run #293](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364954152) attempt 1, not the review report's
own item 6 ("evidence of record is pending"), which the Manager had already resolved with run #292.

**Commits**

| Commit | What |
|---|---|
| `627fff0` | RED tests for findings 1–3 (10 cases) |
| `0b58fbd` | GREEN: findings 1–3 in `scripts/check_install_guide.py`; the reason test follows the new `GUIDE_ONLY` shape; 2 boundary tests |
| `0a92489` | finding 6: the Guide 8 stop loop in the workflow and its CI-only entry |
| this commit | documentation only: this section, Status, and the disposition table of the review record |

**What changed, per finding**

1. *Guide-only lines are checked in place.* Each `GUIDE_ONLY` entry is now `line: (reason, next compared command)`.
   After the exactly-once check, the guide's guide-only lines, each paired with the next compared guide command after
   it (or the end of the guide), must equal the `GUIDE_ONLY` list in its order. The seven `export` lines must come
   right before `psql -d postgres -tAc 'SHOW server_version'`; `git clone …` and `cd ERP-for-Factory` right before
   the first `sed -e …` line of step 4; the guide's foreground `runserver` line right before
   `… seed_production_demo --reset`. Anchoring was chosen over "list order only" because list order alone does not
   reject `cd ERP-for-Factory` moved to just after the `sed` command. On a difference the check prints the expected
   and the found line with the next compared command of each.
2. *Exactly once; unique step names.* Both allow-lists are counted with `collections.Counter`: an entry that matches
   0 times fails as "not used" (finding 5, kept), more than once as "matched more than once" with the count (guide
   side: with the INSTALL.md line numbers). `job_steps()` fails when two steps of the job `install-guide` have the same
   name, naming both workflow lines; all steps count, including `uses:` steps.
3. *`sh` / `shell` fences fail.* Outside a ` ```bash ` block, a fence line that starts with ` ``` ` or `~~~` and whose
   info string's first word is `sh` or `shell` (any letter case) fails with its INSTALL.md line number. **Chosen
   scope:** other fences are not rejected (the ruling names `sh` and `shell`, and an output block such as ` ```text `
   may be wanted in the guide; a test shows ` ```text ` passes). **Remaining limit:** a command in a ` ```console `,
   ` ```zsh ` or unlabelled fence is still not read. **Also a known limit** (re-review finding 1, owner [comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755): recorded,
   no code change): a ` ```bash title=x ` fence (info string with attributes), a `~~~bash` fence and a four-backtick
   ` ````sh ` fence are neither read nor rejected, so commands in them bypass the check.
4. **Known limit, not changed** (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)):
   only `name:` and `run:` of each step are read. Step-level keys `if:`, `working-directory:`, `shell:`,
   `continue-on-error:` and per-step `env:` are not compared. For example, `continue-on-error: true` on the check step
   itself would turn the check off while the check still passes, and `if: false` on a guide step would skip its
   commands. Such edits show in the workflow diff, which the owner reviews. **Also a known limit** (re-review, owner
   [comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)): the check does not verify its own position — moving the step "CI-only: guide and job commands match" away
   from right after "Guide 4: Get the code" still passes; this too is protected only by workflow-diff review.
5. **Kept** (owner, same comment): the check fails on an allow-list entry that matches nothing.
6. *runserver stop.* In run #293 attempt 1 ([job 131687066384](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364954152/job/131687066384)),
   2 s after `pkill` two processes still matched (`4714`, `4720`) and the step failed with "runserver still running";
   attempt 2 passed. In step "Guide 8: Run and log in", `sleep 2` became
   `for i in $(seq 1 20); do pgrep -f 'manage.py runserver' > /dev/null || break; sleep 1; done`: it checks every
   second for up to 20 s and stops as soon as no process matches; the unchanged
   `if pgrep -f 'manage.py runserver'; then echo "runserver still running"; exit 1; fi` then fails only after the
   limit. The `# CI-only: stop the server.` comment is unchanged; no guide command changed. This changes an existing
   M7.2 CI-only line of the job, which "Not in scope" excludes; the owner approved this change
   ([comment 6877846545](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6877846545)). The
   CI-only entry `(GUIDE_8, "sleep 2")` became the loop line, still citing M7.2 CI-only item 5.

**RED, then GREEN** (development checks; uv 0.11.32)

| Run | Tree | Python | Result |
|---|---|---|---|
| `uv run pytest tests/ci -q` | `627fff0` | 3.14.8 | **10 failed**, 27 passed; every failure is `assert 0 == 1` with the check's OK line (the old script passes all 10 cases) |
| `uv run pytest tests/ci -q` | `0b58fbd` | 3.14.8 | **39 passed** (4 other + 35 install-guide tests) |
| `uv run pytest tests/ci -q` | `0a92489` | 3.14.8 | **39 passed** |
| `uv run --no-project --isolated --python /usr/bin/python3.12 --with pytest==9.1.1 python -m pytest -q -p no:cacheprovider tests/ci/test_install_guide_check.py`, on a `git archive` copy of each commit | `627fff0` / `0b58fbd` / `0a92489` | 3.12.3 | 10 failed, 23 passed / **35 passed** / **35 passed** |

The 10 RED cases: (1) `cd ERP-for-Factory` moved to a new bash block at the end (reviewer probe P2), moved to after
`.env.example > .env`, swapped with `git clone`; `export PGPORT=5432` duplicated; (2) `seed_production_demo`
duplicated inside the seed-rerun step (probe P10); `pkill` duplicated in Guide 8; a second step named
"Guide 8: Run and log in" before "Guide 4: Write .env" (probe P8); "Guide 9" renamed to "Guide 7: Load the demo
data"; (3) a ` ```sh ` and a ` ```shell ` block. Added with GREEN (passing from the start): the guide's `runserver`
line moved to before `migrate` must fail; a ` ```text ` block must pass.

Mutation check (`0b58fbd` script, one check disabled at a time, restored and checked with `cmp`): without the place
check 4 tests fail (the 3 moved/swapped cases and runserver-before-migrate); without the exactly-once check 3 fail;
without the duplicate step-name check 2 fail; without the fence check 2 fail.

Finding 6 stop lines, run locally with `bash -e` on the lines copied from the workflow, against a dummy background
process whose command line contains `manage.py runserver`: one that exits 3 s after SIGTERM → exit 0 after 4.06 s
(early exit; the old `sleep 2` lines fail on the same dummy with "runserver still running"); one that ignores SIGTERM
→ "runserver still running", exit 1 after 20.17 s.

**Other checks** (`0a92489`, development checks)

- `/usr/bin/python3.12 -I -X dev -W error scripts/check_install_guide.py` (Python 3.12.3) and `python3 -I -X dev -W
  error …` (3.13.18) → `install guide check OK: 23 commands match in order (allow-listed: 10 guide-only lines, 25
  CI-only lines)`, exit 0. `python3.12 -m py_compile` and `python3.11 -m py_compile` succeed. Imports: `argparse`,
  `sys`, `collections.Counter`, `pathlib` (stdlib only); `git diff --quiet origin/main -- pyproject.toml uv.lock` →
  unchanged.
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `278 files already formatted`;
  `git diff --check origin/main` → no output.
- Workflow against `git show origin/main:.github/workflows/foundation.yml`: `  install-guide:` starts at byte 7436 in
  both; `head -c 7436` of both are equal (`cmp`), so `postgresql-tdd` and `report` are byte-for-byte unchanged.
  `git diff --numstat origin/main` → `6 1` (the check step of `068d65f`, +5, and the one replaced line);
  `git diff 6e4526c 0a92489 -- .github/workflows/foundation.yml` → only `sleep 2` replaced by the loop line.
- The full suite on PostgreSQL was not rerun in this round (no Django or app code changed); CI runs it.

### Repair round 2 (2026-11-14)

The final repair round. Done by a sub-agent spawned by the Manager (Implementer role), on `claude/vibrant-sagan-ivztik`
from `1553e7c`. All runs below are **development checks** in that sub-agent's container, not CI; CI on PostgreSQL
18.6 stays the evidence of record ([the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964), latest head, not changed for this round),
and the merge criterion is 3/3 checks passing on the PR page (owner).

**The failure.** [Run #296](https://github.com/porntaned/ERP-for-Factory/actions/runs/43601378350) (head `1553e7c`),
[job 132466649783](https://github.com/porntaned/ERP-for-Factory/actions/runs/43601378350/job/132466649783) `install-guide`,
step "Guide 8: Run and log in": the HTTP checks passed (`login page: 200`, `login POST: 302`, the balance row) at
13:49:18Z; after `pkill -f 'manage.py runserver'` the 20 s wait loop ran out and the stop check printed `4161`,
`4166`, `runserver still running`, exit 1 at 13:49:38Z. The step printed nothing else about the two processes, so the
root cause is not known. The runserver log (step "CI-only: runserver log") ends with Django's normal start banner
and shows no shutdown. Same symptom as run #293 attempt 1 (see [Repair round 1](#repair-round-1-2026-11-14), item 6).

**Owner ruling (verbatim).** [Issue #119 comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215) (2026-11-14):

```text
คำตัดสินเรื่อง runserver ค้าง (run #296) — รอบแก้ที่ 2 (รอบสุดท้าย):
- ใช้ A + C: เมื่อครบเวลารอแล้วยังมี process ค้าง ให้พิมพ์ ps -o pid,ppid,stat,etime,cmd ของ process ที่ค้าง
  แล้ว pkill -9 เก็บกวาด และพิมพ์ว่าใช้ทางสำรอง; job ล้มเฉพาะเมื่อ pkill -9 แล้วยังไม่ปิด
- แก้เฉพาะบรรทัด CI-only ใน step "Guide 8" และ allow-list ห้ามแก้คำสั่งในคู่มือ ห้ามแตะ postgresql-tdd และ report
- independent review โดย session แยกตัวใหม่ (ไม่ใช่ 2 ตัวก่อน) ตรวจเฉพาะ diff ของรอบนี้
- ถ้ารีวิวเจอแค่ low/info: บันทึกเป็นข้อจำกัดตามกติกาข้อ 1 ไม่ต้องถาม
- ถ้าหลังแก้ install-guide ยังล้ม: ห้ามแก้รอบที่ 3 หยุดแล้วส่ง log ให้ผม
- CI comment ไม่ต้องแก้ เกณฑ์ merge คือ check 3/3 ผ่านบนหน้า PR
```

The owner also asked (as relayed by the Manager) for tests of the allow-list for this change.

**Commits**

| Commit | What |
|---|---|
| `905ca51` | RED tests for the new allow-list (12 cases) |
| `1922d9a` | GREEN: the Guide 8 stop lines in the workflow and their CI-only entries |
| this commit | documentation only: this section, Status, Roles, Review, the acceptance-criteria notes and the allow-list table |

**What changed.** In step "Guide 8: Run and log in", under the unchanged `# CI-only: stop the server.` comment,
`pkill -f …` and the 20 s wait loop are unchanged; the last line
`if pgrep -f 'manage.py runserver'; then echo "runserver still running"; exit 1; fi` was replaced by one `# CI-only:`
comment and seven lines:

```bash
# CI-only: still running after 20 s (run #296): show the processes, then pkill -9; fail only if that fails too.
if pids=$(pgrep -d, -f 'manage.py runserver'); then
  echo "runserver did not stop after SIGTERM; fallback: pkill -9"
  ps -o pid,ppid,stat,etime,cmd -p "$pids" || true
  pkill -9 -f 'manage.py runserver' || true
  for i in $(seq 1 5); do pgrep -f 'manage.py runserver' > /dev/null || break; sleep 1; done
  if pgrep -f 'manage.py runserver'; then echo "runserver still running after pkill -9"; exit 1; fi
fi
```

When SIGTERM works, `pgrep` finds nothing, the `if` body does not run and the step prints nothing extra. Under the
step's `bash -e` (run #296 shows `shell: /usr/bin/bash -e {0}`), commands in an `if` condition, left of `||` and in a
`for` body after `||` do not end the step; `ps` (exit 1 if every listed PID has already gone) and `pkill -9` (exit 1
if nothing matched any more) end in `|| true`, because the last `pgrep` decides. The step's own command line is the
temp-file path, so it never matches `pgrep -f`, and `pgrep` never matches itself. No guide command changed; this again
changes an existing M7.2 CI-only line of the job, which "Not in scope" excludes; the owner approved it.

**Allow-list** (`scripts/check_install_guide.py`): the `(GUIDE_8, "if pgrep … \"runserver still running\"; exit 1;
fi")` entry was replaced by seven `(GUIDE_8, line)` entries, one per new line exactly as the check reads it (the
block indentation removed, so the inner lines keep a 2-space prefix; the closing line is `fi`), each citing
`M7.2 CI-only item 5`, under a comment citing run #296 and owner comment 6878538215. No other script logic changed.
The check now reports `23 commands match in order (allow-listed: 10 guide-only lines, 31 CI-only lines)` (25 before).

**RED, then GREEN** (development checks; uv 0.11.32; synthetic env `DJANGO_SECRET_KEY=x POSTGRES_DB=x
POSTGRES_USER=x POSTGRES_PASSWORD=x POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432`)

| Run | Tree | Python | Result |
|---|---|---|---|
| `uv run pytest tests/ci -q` | `905ca51` | 3.14.8 | **12 failed**, 39 passed |
| `uv run pytest tests/ci -q` | `1922d9a` | 3.14.8 | **51 passed** (4 other + 47 install-guide tests) |
| `uv run --no-project --isolated --python /usr/bin/python3.12 --with pytest==9.1.1 python -m pytest -q -p no:cacheprovider tests/ci/test_install_guide_check.py`, on a `git archive` copy of each commit | `905ca51` / `1922d9a` | 3.12.3 | 12 failed, 35 passed / **47 passed** (one `Unknown config option: DJANGO_SETTINGS_MODULE` warning: no pytest-django) |

The 12 new tests: the compared lines of Guide 8 end with the 9 stop lines in order and the old stop check is gone;
each stop line is allow-listed in Guide 8 only, citing M7.2 CI-only item 5, and the old entry is gone; each of the 7
fallback lines removed from the workflow fails as "not used" (7 cases); the old stop check put back in place of the
fallback fails as a job line not in the allow-list; `pkill -9 …` moved from Guide 8 to "Guide 9: Start the demo data
again" fails naming Guide 9; the fallback block duplicated fails as "matched more than once". On `905ca51` the first
two fail on their assertions (the new lines are not in the job or the allow-list) and the other 10 fail on the test
helper's precondition (the fallback lines do not exist yet in the workflow).

**Stop logic, run locally** (development check, on the lines of `1922d9a`). A driver script copied the lines after
`# CI-only: stop the server.` up to the blank line out of the workflow (de-indented) into `stop.sh` and ran it with
`bash --noprofile --norc -e -o pipefail stop.sh` against a dummy `python3 …/dummy/manage.py runserver` started in
the background (the driver's and `stop.sh`'s own command lines do not contain the pattern):

| Dummy | Output of `stop.sh` | Exit | Time |
|---|---|---|---|
| exits on SIGTERM | nothing | 0 | 0.02 s |
| exits 3 s after SIGTERM | nothing | 0 | 3.04 s |
| ignores SIGTERM | marker line; `ps` header and the one PID with `PPID`, `STAT S`, `ELAPSED 00:21`, `CMD …manage.py runserver` | 0 | 20.21 s |
| parent and child both ignore SIGTERM (like runserver's autoreloader and its worker) | marker line; `ps` with both PIDs (the child's `PPID` is the parent) | 0 | 20.20 s |
| ignores SIGTERM and a supervisor that does not match restarts it after every kill (the fail path) | marker line; `ps` line; the new PID; `runserver still running after pkill -9` | 1 | 25.24 s |

After each case nothing matched any more. A process that survives SIGKILL itself (e.g. in uninterruptible sleep) was
not reproduced; the respawn case exercises the same final check.

**Other checks** (`1922d9a`, development checks)

- `/usr/bin/python3.12 -I -X dev -W error scripts/check_install_guide.py` (3.12.3) and `python3 -I -X dev -W error …`
  (3.13.18) → the OK line above, exit 0.
- `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `278 files already formatted`;
  `git diff --check` → no output.
- Workflow against `git show origin/main:.github/workflows/foundation.yml` (`4f6c065`): `  install-guide:` starts at
  byte 7436 in both; `head -c 7436` of both are equal (`cmp`), so `postgresql-tdd` and `report` are byte-for-byte
  unchanged. `git diff 1553e7c 1922d9a -- .github/workflows/foundation.yml` → one hunk in Guide 8: 1 line removed,
  8 added (the comment and the 7 lines). The workflow parses as YAML (PyYAML in an isolated `uv run --with pyyaml`,
  not a project dependency) and the Guide 8 `run:` ends with the lines above.
- The guide's ` ```bash ` lines are unchanged against `origin/main`, and `docs/INSTALL.md` is unchanged against
  `1553e7c`.

**Known limits** (this round)

- The cause of the stuck processes is still unknown; the fallback prints `ps` for them so the next occurrence shows
  their parent, state and age. If it happens, the step passes with the marker line in the log.
- The check matches CI-only lines per step as a set, not in order; the order of the stop lines is pinned by the test
  `test_r2_guide_8_ends_with_the_stop_lines_in_order`, not by the check script.

## Closeout (2026-11-15)

[PR #121](https://github.com/porntaned/ERP-for-Factory/pull/121) was merged by the owner on GitHub at 2026-11-14T16:34:51Z as merge commit
`6f6dd2bbc894538e489d4e7d5a3156ca549b7a8a` (head `3c8abc8`); the owner reported it in chat. No session merged it.
- [PR CI #298](https://github.com/porntaned/ERP-for-Factory/actions/runs/43604628567) on `3c8abc8`: `postgresql-tdd` (PostgreSQL 18.6 / Python 3.14.8,
  **1207 passed**, [CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964)), `install-guide` and `report` all passed on
  attempt 1; `install-guide` did not use the `pkill -9` fallback.
- [Main CI #299](https://github.com/porntaned/ERP-for-Factory/actions/runs/43616383958) on `6f6dd2b`: all 3 jobs passed on attempt 1; `postgresql-tdd`
  **1207 passed** ([CI comment](https://github.com/porntaned/ERP-for-Factory/commit/6f6dd2bbc894538e489d4e7d5a3156ca549b7a8a#commitcomment-210026954)); `install-guide` check step OK,
  1207 passed, login 200, no `pkill -9` fallback (read from the job log).
- Reviews: three independent reviews by three separate sessions, all ship —
  `session_01MVmjhg9gAi1DN28QQBeVER` (head `aae03d8`), `session_01MVmjhfwZuoJ19Fys5UNKmE` (head `c052f4c`, after repair
  round 1) and `session_01MVmjhdTUAG56qPZmJnVeJn` (round-2 diff `1553e7c..34211ef`) — recorded in
  [the review record](../reviews/i119-independent-review.md). Two repair rounds (the limit). Implementer = sub-agents of
  the Manager; Manager = session `session_01MVmjhdAZRZbr6kL22x7hby`.
- Known limits stay as recorded above (step-level keys, the check's own position, some fence forms, CI-only order within
  a step, a silent `pkill -9` fallback, the unknown root cause of stuck runserver processes).
- No deployment.

## Handoff (2026-11-15)

1. **Task and role actually performed:** Manager session `session_01MVmjhdAZRZbr6kL22x7hby` ran Issue #119 end to end:
   - spec and the owner's approval;
   - Implementer sub-agents for the implementation and repair rounds 1–2;
   - three independent reviews by three separate sessions;
   - the post-merge docs PR [PR #122](https://github.com/porntaned/ERP-for-Factory/pull/122).

   The owner merged PR #121 on GitHub. No session merged it.
2. **Files and behavior changed:**
   - `scripts/check_install_guide.py` and `tests/ci/test_install_guide_check.py` (51 tests);
   - in job `install-guide`: the check step, and the runserver stop with its `ps` + `pkill -9` fallback;
   - one sentence each in `docs/INSTALL.md` and `docs/DEVELOPMENT.md`.

   `postgresql-tdd` and `report` are byte-identical to the base.
3. **Commands and results:** see [Evidence](#evidence), [Repair round 1](#repair-round-1-2026-11-14),
   [Repair round 2](#repair-round-2-2026-11-14) and [Closeout](#closeout-2026-11-15):
   - PR CI #298 and main CI #299: 3/3 on attempt 1, 1207 passed;
   - the `pkill -9` fallback has not been used since it was added.
4. **Commits:**
   - Issue #119 is merged at `6f6dd2b`.
   - This post-merge record is on branch `claude/vibrant-sagan-ivztik` in [PR #122](https://github.com/porntaned/ERP-for-Factory/pull/122), which is open and awaiting the owner's merge on GitHub. Its merge SHA goes into the next post-merge docs PR (No chain).
5. **Findings and remaining risks:** the known limits in the Closeout. The root cause of the runserver processes that
   would not stop (runs #293, #296) is still unknown; if the fallback is ever used, the job log shows `ps` output.
6. **Owner decisions recorded:**
   - D1–D4 ([comment 6842699856](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6842699856));
   - the repair-round rulings;
   - A+C for the runserver stop ([comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215));
   - standing rules 1–6 ([comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755));
   - rules 7–8 (chat, 2026-11-15).

   All eight are in [`docs/MULTI_AGENT.md`](../MULTI_AGENT.md).
7. **Still open:**
   - [PR #122](https://github.com/porntaned/ERP-for-Factory/pull/122) awaits the owner's merge.
   - [Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119) is still open; the owner closes it.
   - No other branch or PR is pending.
8. **Next work and who does it:**
   - **M7.3** (Architecture and Domain diagrams that match the code) runs in a **new Manager session**.
   - It starts only after the owner approves it in a comment on its new Issue (rule 6).
   - Per rule 7 it needs no separate reviewer session, unless it touches business code, the database or permissions.
   - Then M7.4 and M7.5 (M7.5 = final Scrutinize: independent review by a separate session).
   - This session stops after reporting PR #122's CI.
