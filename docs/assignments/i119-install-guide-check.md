# Issue #119 — Keep `docs/INSTALL.md` and the `install-guide` CI job identical

Repository `porntaned/ERP-for-Factory`; branch `claude/vibrant-sagan-ivztik` (restarted from `main` `4f6c065` after
PR #120 merged); [Issue #119](https://github.com/porntaned/ERP-for-Factory/issues/119).
Status: **spec approved by the owner; implementation not started.**

Owner approval: [Issue #119 comment](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6842699856)
(2026-11-13) and the owner's chat message of the same day.

Roles (as they actually happen; updated as work proceeds):
- **Manager** = Claude Code session `session_01MVmjhdAZRZbr6kL22x7hby`.
- **Implementer** = a sub-agent spawned by the Manager (not started yet).
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

Not started.
