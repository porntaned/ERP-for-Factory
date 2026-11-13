Type: independent review by a separate session (session_01MVmjhg9gAi1DN28QQBeVER); reviewed commit `aae03d8aac4a215f433c9be904098a625d784045` (PR #121 head, branch `claude/vibrant-sagan-ivztik`), base `main` `4f6c065`.

The Reviewer session was created by the Manager session (`session_01MVmjhdAZRZbr6kL22x7hby`) and was given only the
PR number, the Issue number and the spec path (plus the Reviewer role rules: read-only, Scrutinize, no merge, no
GitHub comments). "Report" below is the Reviewer's final message as received (2026-11-13), copied by the Manager
without edits. "Manager disposition" is the Manager's own and is not part of the review.

## Report

# Independent review: PR #121 (Issue #119)

- **Type:** independent review by a separate Claude Code session. This is not a sub-agent of the Manager. The session was given only the PR number, the Issue number and the spec path.
- **Reviewer session:** `session_01MVmjhg9gAi1DN28QQBeVER`
- **Date:** 2026-11-13
- **Head reviewed:** `aae03d8aac4a215f433c9be904098a625d784045` (`claude/vibrant-sagan-ivztik`)
- **Base:** `main` `4f6c065ba4523b28aa4d848128dedf0771f27bb4` (this is also the merge-base)
- **Mode:** read-only. Nothing was edited, committed, pushed or commented. All probes ran on copies in the reviewer's scratchpad.

## 1. Intent

**Goal:** CI must fail when the bash commands in `docs/INSTALL.md` and the `run:` lines of the `install-guide` job differ, apart from the allow-listed lines, each of which states its reason.

**Should this change exist?** Yes. It closes M7.2 review finding 3. Without it, the two files can drift apart while CI stays green.

**Is there a simpler way?** Generating the job from the guide, or running the guide's blocks directly, would remove the duplication altogether. The owner explicitly excluded both ("making CI extract and run the guide's blocks itself"). PyYAML is excluded as a dependency (D3). Within those rulings, a stdlib text reader with two exact-line lists is the smallest design that fits. I found no simpler option that the owner's rulings allow.

## 2. Trace

### Entry point

The new step `.github/workflows/foundation.yml:257-258` runs `python3 scripts/check_install_guide.py` with no arguments. `main()` then reads `ROOT/docs/INSTALL.md` and `ROOT/.github/workflows/foundation.yml`, where `ROOT = Path(__file__).resolve().parents[1]`. Because the paths come from the script's own location, the step works from any working directory. The job sets no `defaults.run.working-directory`.

### Guide side

`guide_lines()` reads the lines between a line that strips to exactly ` ```bash ` and the next line that strips to ` ``` `.
- A `#` line inside a bash block raises an error (D4).
- An unclosed block raises an error.
- A guide with no bash block raises an error.

`docs/INSTALL.md` has 9 bash fences (lines 28–168) and no other fences.

### CI side

`job_steps()` walks the workflow like this:
1. Finds `jobs:`.
2. Finds the job header at the indentation of the first job.
3. Finds `steps:` and splits it into `- ` items.
4. Reads `name:` and `run:` at the key indentation of each item.

`_run_lines` accepts only two `run:` forms:
- `|`, read as a block scalar: the first line's indentation is removed, a less indented line ends the block, trailing blanks are clipped.
- a plain one-line value.

Any other form (`|-`, `>-`, quoted, `|` followed by a comment) raises an error. I confirmed this with probe P11: `run: | # x` gives "unsupported `run:` form", exit 1. `ci_lines` then drops lines that start with `#` (D4).

### Compare

`compare()` works in four steps:
1. Removes guide lines found in `GUIDE_ONLY`, matched by line text.
2. Removes CI `(step, line)` pairs found in `CI_ONLY`.
3. Compares what remains, index by index, and on the first difference prints both sides.
4. Fails if any allow-list entry matched nothing.

### Seams with unchanged code

- `report` sits between `postgresql-tdd` (line 17) and `install-guide` (line 200), so the 7436-byte prefix check covers both jobs.
- `install-guide` runs the full suite with `uv run --env-file .env pytest` (line 278), which collects `tests/ci`. `postgresql-tdd` collects it in its full-suite step (line 142). Neither job needed a change to run the new tests.

## 3. Verify

### Claims I verified

| Claim | Path / command | Observed |
|---|---|---|
| Head and base | `git rev-parse HEAD origin/main; git merge-base` | `aae03d8…`, `4f6c065…` |
| Real files pass on 3.13 | `python3 -I scripts/check_install_guide.py` (3.13.18) | `OK: 23 commands match in order (allow-listed: 10 guide-only lines, 25 CI-only lines)`, exit 0 |
| Real files pass on 3.12 | `/usr/bin/python3.12 -I -X dev -W error scripts/check_install_guide.py` | same output, exit 0 |
| Tests pass on 3.12 | `uv run --no-project --isolated --python /usr/bin/python3.12 --with pytest==9.1.1 python -m pytest -q tests/ci` | **27 passed** |
| Tests pass on 3.13 | same command with `python3` (3.13.18) | **27 passed** |
| Tests pass on 3.14 | not verified: no 3.14 interpreter in this container (`uv run` reports none for 3.14.8) | — |
| Stdlib only, no new dependency | script imports `argparse`, `sys`, `pathlib`; `git diff --quiet origin/main -- pyproject.toml uv.lock` | unchanged |
| `postgresql-tdd` and `report` byte-identical | `head -c 7436` of both versions piped to `cmp` | equal |
| Workflow diff is one step, right after "Guide 4: Get the code" | `git diff origin/main...HEAD -- .github` | one hunk, +5/−0, at lines 255–259 |
| Existing `install-guide` commands unchanged | same diff | no other hunk |
| Lint | `uv run ruff check scripts tests/ci`, `ruff format --check` | clean, no output |
| Every allow-list entry cites a reason | read `GUIDE_ONLY` and `CI_ONLY` | every entry's value is "M7.2 CI-only item 2/4/5/6/7" or "owner ruling D1"; items 1 and 3 have no entry, which is correct |
| Failure cases (a)–(i) have tests | `grep '^def test_'` | (a), (b), (c), (d)×2, (e), (f) on both sides, (g) parametrized, (h)×5, (i)×2, plus a test for an unused entry |
| Docs sentence | diffs of `docs/INSTALL.md` and `docs/DEVELOPMENT.md` | prose only; the 9 bash blocks are unchanged |
| CI on PostgreSQL 18.6 | PR check runs | **in progress at review time** for `postgresql-tdd` and `install-guide` ([run 43364021863](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364021863)); no CI comment yet |

### Claims I did not verify (taken from the PR)

- RED first at `86732bd`.
- Full suite of 1183 passed on PostgreSQL 16.15.
- The Implementer's mutation check.
- The 3.14.8 runs.

### Adversarial probes

Each probe edits a tmp copy of the real files and passes it with `--guide` / `--workflow`.

| # | Input | Result | Expected? |
|---|---|---|---|
| P2 | `cd ERP-for-Factory` moved from guide step 4 to a new bash block at the end of the guide | **OK, exit 0** | gap (finding 1) |
| P4 | `working-directory: /tmp` added to "Guide 4: Write .env" | OK, exit 0 | out of scope (finding 4) |
| P5 | `continue-on-error: true` added to the check step itself | OK, exit 0 | out of scope (finding 4) |
| P6 | `if: false` added to "Guide 4: Write .env" | OK, exit 0 | out of scope (finding 4) |
| P8 | a second step named "Guide 8: Run and log in" with `run: sleep 2`, placed before "Guide 4: Write .env" | **OK, exit 0** (26 CI-only lines) | gap (finding 2) |
| P9 | a guide command in a ` ```sh ` block | **OK, exit 0**; the line is not read | gap (finding 3) |
| P10 | `seed_production_demo` repeated inside the seed-rerun step | **OK, exit 0** (26 CI-only lines) | gap (finding 2) |
| P11 | `run: \| # x` | FAILED with "unsupported `run:` form", exit 1 | correct |
| P12 | guide with CRLF line endings | OK; `read_text` turns `\r\n` into `\n` | correct |

## 4. Findings, most severe first

None of the findings blocks the acceptance criteria. All are low or informational.

### 1. Low: guide-only lines are removed wherever they appear in the guide

**Where:** `scripts/check_install_guide.py:22-36` and `compare()` at line ~281 (`entry[1] not in GUIDE_ONLY`).

**Why it matters:** The guide's own order is part of what a reader follows. If `git clone` or `cd ERP-for-Factory` is moved after commands that need the repository, or the guide's foreground `runserver` line is moved before `migrate`, the guide breaks and the check stays green. The CI job would not notice either, because it never runs those lines.

**Evidence:** P2 returns OK with exit 0.

**Smallest change:** Anchor each guide-only entry to the compared line that must follow it, for example `cd ERP-for-Factory` before the `.env` `sed` line. A cheaper alternative is to require the guide-only entries to appear in the order the dict lists them, and each exactly once. If the owner prefers to keep D2 (a) exactly as written, record this as a known limit in the spec instead.

### 2. Low: matches are counted as "at least once", not "exactly once", and step names may repeat

**Where:** `compare()` uses `ci_seen = set(ci)` and `guide_seen = {…}`, and removes every occurrence of an allow-listed pair. `job_steps()` does not reject two steps with the same name.

**Why it matters:**
- A CI-only line can be repeated inside its own step (P10).
- A second step can reuse an allowed step's name, such as "Guide 8: Run and log in" or the seed-rerun name. It can then run any allow-listed line of that step anywhere in the job (P8). This partly bypasses the step scoping that case (i) is meant to guarantee.
- The same applies on the guide side: an `export` line can be duplicated anywhere.

**Evidence:** P8 and P10 return OK with exit 0.

**Smallest change:**
- In `job_steps()`, fail on duplicate step names in the job.
- In `compare()`, count matches with `collections.Counter` (stdlib) and require each allow-list entry to match exactly once. All entries match exactly once in today's files.
- Add one test for each.

### 3. Low: commands outside ` ```bash ` fences are not read

**Where:** `guide_lines()`, which treats only a fence that strips to exactly ` ```bash ` as a command block.

**Why it matters:** A later editor could add a command in a ` ```sh `, ` ```shell `, ` ```console `, unlabelled or `~~~` fence, and the check would never see it (P9). This matches the spec's wording ("the bash blocks"), so it is a gap in the spec rather than a defect against it. Today the guide has only ` ```bash ` fences.

**Smallest change:** Fail on any fence in `docs/INSTALL.md` other than ` ```bash ` / ` ``` `, with a message that names the line. Add one test.

### 4. Info: step-level keys are not compared

**What is not compared:** `if:`, `working-directory:`, `shell:`, `continue-on-error:` and per-step `env:`.

**Evidence:** P4, P5 and P6 return OK. P5 is the notable one: setting `continue-on-error: true` on the check step itself turns the check off and the check still passes.

**Assessment:** All of this is outside the spec, which compares `run:` lines, and any such edit shows plainly in a workflow diff. No change is required. Mentioning it in the spec's Evidence section as a known limit would keep the claim "CI fails when they differ" accurate.

### 5. Info: the "unused allow-list entry" check goes beyond the spec

**What:** The Implementer added it, and the PR body asks the owner to confirm it.

**Assessment:** I support keeping it. It is what makes each entry stay tied to a real line. Without it, a changed CI-only command would leave a stale entry while the changed command fails as an extra line, so the error would be clear in either case. The owner's confirmation is still needed because the spec does not mention this check.

### 6. Info: evidence of record is pending

At review time, CI on PostgreSQL 18.6 for head `aae03d8` was in progress: `postgresql-tdd` [job 131684043825](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364021863/job/131684043825) and `install-guide` [job 131684043453](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364021863/job/131684043453). There was no CI comment yet. I also could not run the 3.14 leg of "runs on 3.12 and 3.14". 3.12 and 3.13 pass. The full suite run inside CI is 3.14 evidence.

## 5. Checked against the spec's acceptance criteria

| Criterion | Status |
|---|---|
| RED first, then GREEN; (a)–(i) proven; real files pass | GREEN and (a)–(i) verified on 3.12 and 3.13; RED taken from the commit record |
| Every entry cites an M7.2 item or D1; none without a reason | verified |
| Stdlib only; `pyproject.toml` and `uv.lock` unchanged; nothing newer than 3.12 | verified (passes with `-X dev -W error` on 3.12.3) |
| Step right after "Guide 4: Get the code"; `postgresql-tdd` and `report` byte-identical; other commands unchanged | verified |
| CI on 18.6 passes all 3 jobs | **pending** |
| 0 broken relative links; ruff clean | ruff verified; the two new links (`../scripts/check_install_guide.py` from `docs/`) resolve to the file |
| Independent review by a separate session | this document |

## Verdict

**ship**, once the pending PostgreSQL 18.6 CI run is green (an acceptance criterion already). The change does what the spec and the owner's rulings require, and every item on the spec's list was traced and passes. Findings 1–3 are real but narrow: a hostile or careless reorder, duplicate, or non-bash fence can pass the check. They are cheap to close in at most one repair round (`Counter`, duplicate-name rejection, a fence check, anchoring the guide-only lines). Otherwise they can be recorded as known limits. None of them lets an ordinary one-sided edit of a command slip through, which is the drift Issue #119 was opened for.

## Manager disposition (Manager session, 2026-11-13; no repair made yet)

| # | Disposition |
|---|---|
| 1 | Owner to decide: anchor/order the guide-only lines (code change, repair round 1) or record as a known limit. |
| 2 | Owner to decide: reject duplicate step names and require exactly-once matches (code change, repair round 1) or record as a known limit. |
| 3 | Owner to decide: fail on any non-` ```bash ` fence in `docs/INSTALL.md` (code change, repair round 1) or record as a known limit. |
| 4 | Not changed (outside the spec); to be recorded as a known limit in the spec if the owner agrees. |
| 5 | Owner to confirm the unused-entry check (also asked in the PR body). |
| 6 | Resolved after the review: PR CI [#292](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364021863) on `aae03d8` passed all 3 jobs on PostgreSQL 18.6 (`postgresql-tdd` 1183 passed per [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964); `install-guide` success; `report` success). |
