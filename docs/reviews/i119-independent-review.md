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

## Manager disposition (Manager session, 2026-11-13; updated 2026-11-14 after repair round 1)

| # | Disposition |
|---|---|
| 1 | **Fixed** in [repair round 1](../assignments/i119-install-guide-check.md#repair-round-1-2026-11-14) (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)): each guide-only line must come right before the compared command its entry names, exactly once, in list order. ("Owner to decide: anchor/order the guide-only lines (code change, repair round 1) or record as a known limit." held until 2026-11-14 — historical.) |
| 2 | **Fixed** in [repair round 1](../assignments/i119-install-guide-check.md#repair-round-1-2026-11-14) (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)): every allow-list entry must match exactly once; duplicate step names in `install-guide` fail. ("Owner to decide: reject duplicate step names and require exactly-once matches (code change, repair round 1) or record as a known limit." held until 2026-11-14 — historical.) |
| 3 | **Fixed** in [repair round 1](../assignments/i119-install-guide-check.md#repair-round-1-2026-11-14) (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)): a ` ```sh ` or ` ```shell ` block in `docs/INSTALL.md` fails; other non-bash fences are not rejected (recorded as a limit in the spec). ("Owner to decide: fail on any non-` ```bash ` fence in `docs/INSTALL.md` (code change, repair round 1) or record as a known limit." held until 2026-11-14 — historical.) |
| 4 | **Known limit**, not changed (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)); recorded in the spec ([repair round 1](../assignments/i119-install-guide-check.md#repair-round-1-2026-11-14), item 4). ("Not changed (outside the spec); to be recorded as a known limit in the spec if the owner agrees." held until 2026-11-14 — historical.) |
| 5 | **Kept** (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)): the check still fails on an unused allow-list entry. ("Owner to confirm the unused-entry check (also asked in the PR body)." held until 2026-11-14 — historical.) |
| 6 | Report item 6: resolved after the review: PR CI [#292](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364021863) on `aae03d8` passed all 3 jobs on PostgreSQL 18.6 (`postgresql-tdd` 1183 passed per [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964); `install-guide` success; `report` success). Owner's "finding 6" (runserver not stopped within 2 s in `install-guide`, [run #293](https://github.com/porntaned/ERP-for-Factory/actions/runs/43364954152) attempt 1; not an item of this Report): **Fixed** in [repair round 1](../assignments/i119-install-guide-check.md#repair-round-1-2026-11-14) (owner, [comment 6877846545](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6877846545)): `sleep 2` replaced by a wait loop of up to 20 s (CI-only line; no guide command changed). |

2026-11-14: the repair (repair round 1) was done by the Implementer sub-agent spawned by the Manager session, not by this
Reviewer; it needs a new independent review by a new separate session (owner, [comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)).

## Re-review

Type: independent review by a separate session (session_01MVmjhfwZuoJ19Fys5UNKmE), a new session — not the first
Reviewer (`session_01MVmjhg9gAi1DN28QQBeVER`) and not a sub-agent of the Manager; reviewed commit
`c052f4cdabf67e373d5d0f8f6f5237103d63f97f` (PR #121 head after repair round 1), base `main` `4f6c065`.

Created by the Manager session and given only the PR number, the Issue number and the spec path (plus the Reviewer
role rules). "Re-review report" is the Reviewer's final message as received (2026-11-14), copied by the Manager
without edits; its own top-level heading is shown one level lower so it nests under this section. "Manager
disposition (re-review)" is the Manager's own and is not part of the review.

### Re-review report

#### Independent review (re-review after repair round 1): PR #121 (Issue #119)

- **Type:** independent review by a separate Claude Code session. This session is not a sub-agent of the Manager and is not the first Reviewer (`session_01MVmjhg9gAi1DN28QQBeVER`).
- **Reviewer session:** `session_01MVmjhfwZuoJ19Fys5UNKmE`
- **Date:** 2026-11-14
- **Head reviewed:** `c052f4cdabf67e373d5d0f8f6f5237103d63f97f` (`claude/vibrant-sagan-ivztik`)
- **Base:** `main` `4f6c065ba4523b28aa4d848128dedf0771f27bb4`, which is also the merge-base.
- **Mode:** read-only. I edited, committed, pushed and commented nothing, and changed no settings. All probes ran on copies in my scratchpad.
- **Repository state:** I fetched every branch ref. The repo is not shallow. The only branch not merged into `main` is `origin/claude/vibrant-sagan-ivztik`, which is this PR.

#### 1. Intent

**Goal:** CI must fail when the bash commands in `docs/INSTALL.md` and the `run:` lines of job `install-guide` differ, apart from allow-listed lines that each state a reason. This round adds four things on top of that:

- It closes first-review findings 1–3 as the owner ruled ([comment 6843916308](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6843916308)).
- It fixes the runserver-stop timing flake, which the owner calls "finding 6" ([comment 6877846545](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6877846545)).
- It records finding 4 as a known limit.
- It keeps the unused-entry check (finding 5).

**Is there a simpler way?** Generating the job from the guide would be simpler, but the owner excluded it, and PyYAML is excluded too. Within those rulings, anchoring each guide-only line to the next compared command is a small and sufficient answer to "check the order of guide-only lines". Plain list order alone would not catch `cd` moved to just after `sed`, so the extra anchoring is justified.

#### 2. Trace (changes since `6e4526c`)

- **`guide_lines()`** (`scripts/check_install_guide.py`, after `REJECTED_FENCES`):
  - Outside a block, a fence that starts with ```` ``` ```` or `~~~` and has the info word `sh` or `shell` (any case) raises an error.
  - A block opens only when the line strips to exactly ```` ```bash ````.
  - A `#` line inside a block raises an error, as before.
- **`job_steps()`:** a `seen` dict rejects duplicate step names. It counts every step, `uses:` steps included, and names both workflow lines. Names are compared after `_unquote`, so a quoted and an unquoted copy of the same name collide (probe Q7).
- **`compare()`** works in this order:
  1. Compares the sequences in order.
  2. `Counter` checks fail on entries matched 0 times ("not used") or more than once.
  3. `_check_guide_only_places()` runs last.
- **`_check_guide_only_places()`:** each guide-only line is paired with the next non-guide-only guide line (or the end of the guide). The pairs are then zipped against `GUIDE_ONLY` in dict order. The two lists have equal length because the exactly-once check ran first.
- **Workflow:** in "Guide 8: Run and log in", `sleep 2` became `for i in $(seq 1 20); do pgrep … > /dev/null || break; sleep 1; done`. The `CI_ONLY` entry was updated to match, still citing M7.2 item 5. `pgrep` sits on the left of `||`, so a non-zero exit does not trip `bash -e`. The step's command line is a temp-file path that does not contain `manage.py runserver`, so `pkill`/`pgrep` cannot match the step itself. That part is unchanged from M7.2.

#### 3. Verify

| Claim | Command / path | Observed |
|---|---|---|
| Head, base, merge-base | `git rev-parse`, `git merge-base` | `c052f4c…`, `4f6c065…`, `4f6c065…` |
| Real files pass on 3.12 | `/usr/bin/python3.12 -I -X dev -W error scripts/check_install_guide.py` | `OK: 23 commands match in order (allow-listed: 10 guide-only lines, 25 CI-only lines)`, exit 0 |
| Real files pass on 3.13 | `python3` (3.13.18) | same, exit 0 |
| Tests pass on 3.12 and 3.13 | `uv run --no-project --isolated --python <py> --with pytest==9.1.1 python -m pytest -q -p no:cacheprovider tests/ci/test_install_guide_check.py` | **35 passed** on both |
| RED for repair round 1 | same command on `git archive` copies, 3.12 | `627fff0`: **10 failed, 23 passed**; `0b58fbd`: **35 passed** |
| Stdlib only; no dependency or AGENTS change | imports `argparse`, `sys`, `collections.Counter`, `pathlib`; `git diff --quiet 4f6c065 HEAD -- pyproject.toml uv.lock AGENTS.md` | unchanged |
| `postgresql-tdd` and `report` byte-identical | `cmp` of `head -c 7436` of both versions | equal |
| Workflow diff | `git diff --numstat` | `6 1`: the check step (+5) right after "Guide 4: Get the code", plus the one replaced stop line |
| Lint | ruff 0.17.1 (version pinned in `uv.lock`, run on 3.12): `ruff check .` and `ruff format --check .` | `All checks passed!`; `278 files already formatted` |
| Whitespace | `git diff --check 4f6c065 HEAD` | no output |
| Stop loop | the 3 lines copied out of the workflow into a file, run with `bash -e` against a dummy that exits 3 s after SIGTERM | exit 0 after 4 s. (My first attempt with `bash -c` killed itself, because `pkill -f` matched its own command line. That is an artifact of my test setup and does not happen in CI.) |
| Tests on 3.14 | not run: no 3.14.8 interpreter in this container | CI's full suite runs on 3.14.8 |
| **CI on PostgreSQL 18.6 for `c052f4c`** | PR check runs | **in progress** at review time: [run 43599732586](https://github.com/porntaned/ERP-for-Factory/actions/runs/43599732586) (`install-guide` job 132461708156, `postgresql-tdd` job 132461707989). The [CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964) still shows `6e4526c`. |

Not verified, taken from the record: the Implementer's mutation checks, the 3.14.8 runs, and the 20.17 s failure path of the stop loop.

##### Adversarial probes

Each probe passes a tmp copy of the real files with `--guide` / `--workflow`.

| # | Input | Result | Assessment |
|---|---|---|---|
| Q12 | two `export` lines swapped | FAILED: place check, expected and found lines shown | correct (finding 1 closed) |
| Q7 | a second step named `Guide 8: Run and log in` (unquoted), placed before "Guide 4: Write .env" | FAILED: duplicate name, both workflow lines named | correct (finding 2 closed) |
| Q5 | indented ```` ```sh ```` block appended | FAILED with the line number | correct (finding 3 closed) |
| Q10 | tab-indented `# comment` in a bash block | FAILED | correct |
| Q9 | workflow with CRLF line endings | OK | correct (`read_text` converts the line endings) |
| Q3 | last fence changed to ```` ```Bash ```` | FAILED: the guide ends early | correct, but only because a real block disappears from the reading |
| **Q1** | new block ```` ```bash title=x ```` with a command, appended | **OK, exit 0**; the command is not read | gap (finding 1 below) |
| **Q6** | new ```` ~~~bash ```` block with a command | **OK, exit 0** | gap (finding 1) |
| **Q4** | new ```` ````sh ```` (four backticks) block | **OK, exit 0** | gap (finding 1) |
| Q13 | check step moved to the end of the job | OK, exit 0 | informational (finding 3) |

#### 4. Findings, most severe first

None of these findings blocks the acceptance criteria. All are low or informational. First-review findings 1, 2, 3 and 6 are closed as ruled, finding 4 is recorded as a limit, and finding 5 is kept.

##### 1. Low: some bash-looking fences are neither read nor rejected, and the spec's list of these limits is incomplete

- **Where:** `guide_lines()`. A block opens only on `line.strip() == "```bash"`. The rejection test looks only at `stripped[3:]` after a 3-character ```` ``` ```` or `~~~`.
- **Why it matters:** these three fence forms would all render as shell blocks to a reader, but their commands bypass the check:
  - ```` ```bash title=x ```` (an info string with attributes)
  - ```` ~~~bash ````
  - ```` ````sh ````. With four backticks the info word parses as `` `sh ``, so it is not rejected.

  The spec's "Remaining limit" lists only ```` ```console ````, ```` ```zsh ```` and unlabelled fences. Its description of the chosen scope ("a fence line that starts with ```` ``` ```` or `~~~`…") also suggests `~~~sh` is the only tilde case. `~~~bash` itself is silently ignored.
- **Evidence:** Q1, Q4 and Q6 all return OK with exit 0.
- **Smallest change:** either option is enough.
  - Code: treat any fence whose first info word, lowercased, is `bash` but that is not exactly ```` ```bash ```` as an error, and strip all leading backticks or tildes before reading the info word. Add one test.
  - Docs only: add these three forms to the spec's remaining-limit sentence.

  The owner's ruling (3) names only `sh` and `shell`, so the docs-only option fully meets the ruling.

##### 2. Low (documentation): the PR body is stale after repair round 1

- **Where:** the PR #121 description.
- **Why it matters:** AGENTS.md requires the PR body to say which commits after a review were documentation only. The body still describes head `aae03d8`, which is now wrong:
  - It gives the workflow diff as "Diff `5 0`" (now `6 1`) and says the existing `install-guide` steps are unchanged (the stop line changed).
  - It reports "27 passed (4 existing + 23 new)" (now 39 in `tests/ci`, 35 in this module).
  - Its commit list ends at `aae03d8`, so `6e4526c`, `627fff0`, `0b58fbd`, `0a92489` and `c052f4c` are missing. Of those, `6e4526c` and `c052f4c` are documentation only.
  - It says nothing about repair round 1 or the owner's finding-6 approval.

  The spec and the review record are up to date, so this concerns only the PR description.
- **Smallest change:** edit the PR body to cover repair round 1, the `6 1` diff with the owner-approved stop-line change, the test counts, the full commit list with docs-only commits marked, and the review status. This needs no commit.

##### 3. Info: Scope 3 and the spec's acceptance criterion still say the `install-guide` commands are unchanged; the check also does not enforce its own position

- **Where:** in `docs/assignments/i119-install-guide-check.md`, Scope item 3 ("Nothing else in the workflow changes… keep their commands") and the acceptance line ("the other `install-guide` commands are unchanged"). The repair section explains the owner-approved exception, but those two lines are not marked as superseded. The project's rule is to mark changed statements as historical rather than leave them.
- **Check position:** the check does not verify its own place. Moving the step to the end of the job still passes (Q13). It is keyed by step name only, and the position under ruling D1 is protected only by diff review, like the step-level keys in limit 4.
- **Smallest change:** add a dated note to those two spec lines that points to repair round 1, item 6. Optionally, mention the step's position under the existing limit 4.

##### 4. Info: evidence of record is pending

- CI for `c052f4c` ([run 43599732586](https://github.com/porntaned/ERP-for-Factory/actions/runs/43599732586)) was in progress at review time.
- The CI comment has not yet updated from `6e4526c`.
- `install-guide` has not yet run with the new stop loop or with the repaired check on the runner's Python 3.12. The acceptance criterion "CI on 18.6 passes all 3 jobs" is open until it does.

#### 5. Checked against the spec's acceptance criteria

| Criterion | Status |
|---|---|
| RED first, then GREEN; (a)–(i) and the round-1 cases proven; real files pass | verified on 3.12 and 3.13: `627fff0` 10 failed, `0b58fbd`/head 35 passed |
| Every entry cites an M7.2 item or D1 | verified, including the replaced stop-line entry (item 5) |
| Stdlib only; no dependency; nothing newer than 3.12 | verified (`-X dev -W error` on 3.12.3) |
| Step right after "Guide 4: Get the code"; `postgresql-tdd` and `report` byte-identical; other commands unchanged | step position and byte-identity verified. One other command changed, with the owner's approval (comment 6877846545). See finding 3. |
| CI on 18.6 passes all 3 jobs | **pending** (run 43599732586) |
| 0 broken relative links; ruff clean | ruff verified; no new links added in this round |
| Independent review by a new separate session | this document |
| At most 2 repair rounds | this is after round 1 |

#### Verdict

**ship**, once CI run 43599732586 on `c052f4c` is green on all three jobs (already an acceptance criterion).

**Biggest reason:** repair round 1 does exactly what the owner ruled. I confirmed each fix with my own probes (Q5, Q7, Q12), the RED → GREEN transition reproduces on Python 3.12, and the jobs that must not change are byte-identical. The remaining items are a narrow fence gap that the spec should name (or that a small code change would close), a stale PR description, and two spec lines that need a historical note. None of them lets an ordinary edit to a command in only one of the two files slip through, which is the drift Issue #119 targets.

### Manager disposition (re-review; Manager session, 2026-11-14; updated the same day after the owner's ruling)

| # | Disposition |
|---|---|
| 1 | **Known limit**, no code change (owner, [comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)): the three fence forms are recorded in the spec (Repair round 1, item 3). ("Owner to decide" held until that ruling — historical.) |
| 2 | The Manager updated the PR body at 13:26 UTC on 2026-11-14, around the time this review started (repair round 1, `6 1` diff, test counts, full commit list with docs-only commits marked); to be re-checked against the final head. |
| 3 | **Fixed (docs only)** per the owner ([comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)): dated historical notes added to Scope 3 and the acceptance line; the check not verifying its own position is recorded as a known limit next to first-review finding 4. ("Owner to decide" held until that ruling — historical.) |
| 4 | Resolved after the review: PR CI [#294](https://github.com/porntaned/ERP-for-Factory/actions/runs/43599732586) on `c052f4c` passed all 3 jobs on attempt 1 (`postgresql-tdd` 1195 passed per [the PR's CI comment](https://github.com/porntaned/ERP-for-Factory/pull/121#issuecomment-6843810964); `install-guide` success, including the check step and the new stop loop; `report` success). |

The owner ruled these items documentation only, needing no new review ([comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)).

## Re-review 2

Type: independent review by a separate session (session_01MVmjhdTUAG56qPZmJnVeJn), a new session — not the first
Reviewer (`session_01MVmjhg9gAi1DN28QQBeVER`), not the re-review session (`session_01MVmjhfwZuoJ19Fys5UNKmE`) and not
a sub-agent of the Manager; reviewed commit `34211efaf9e0eb0fea6c8094f94dbcd6dc24f39c` (PR #121 head after repair
round 2); scope, per the owner (Issue #119 comment 6878538215): only the diff `1553e7c..34211ef`.

Created by the Manager session and given only the PR number, the Issue number, the spec path and the diff range (plus
the Reviewer role rules). "Re-review 2 report" is the Reviewer's final message as received (2026-11-14), copied by the
Manager without edits; its own headings are shown three levels lower so they nest under this section. "Manager
disposition (re-review 2)" is the Manager's own and is not part of the review.

### Re-review 2 report

#### Independent review: Issue #119 repair round 2 (PR #121)

- **Review type:** independent review by a separate session (not the Manager, the Implementer or either earlier Reviewer)
- **Session:** `session_01MVmjhdTUAG56qPZmJnVeJn`
- **Date:** 2026-11-14
- **Head reviewed:** `34211efaf9e0eb0fea6c8094f94dbcd6dc24f39c` (same as `origin/claude/vibrant-sagan-ivztik`)
- **Diff base:** `1553e7c8a8f81bc184679068d6a92a1e7bfceeff`. Scope is `1553e7c..34211ef` only, per the owner.
- **Commits:** `905ca51` (red tests), `1922d9a` (the workflow fix and the allow-list), `34211ef` (documentation only)
- **Mode:** read-only. I edited, committed, pushed and commented nothing.

##### 1. Intent

**Goal:** In the `install-guide` job, step "Guide 8: Run and log in" failed in run #296 because runserver was still running 20 s after SIGTERM. When that happens, the step should now print the stuck processes with `ps` and kill them with `pkill -9`. The step fails only if they survive that too. The allow-list in `scripts/check_install_guide.py` and the tests follow the new lines. This is what the owner ruled in comment 6878538215 ("A + C").

**Simpler alternative:** Plain `pkill -9` with no `ps` would also make CI pass, but it would hide even the evidence of the stuck processes. The owner asked for the `ps` output explicitly. The 7-line block is about as small as that ruling allows.

**Scope check (owner ruling):**
- Only CI-only lines in Guide 8 and the allow-list changed.
- `docs/INSTALL.md` is unchanged in this diff (`git diff --stat 1553e7c..34211ef -- docs/INSTALL.md` prints nothing).
- `postgresql-tdd` and `report` are unchanged. I checked it like this:
  - `install-guide:` starts at byte 7436 in both `origin/main` and `34211ef`, and it is the last job in the file.
  - `cmp` of the first 7436 bytes of the two files: equal.

##### 2. Trace

**Workflow, lines 306–315 of `foundation.yml` at `34211ef`.** The step runs under `bash -e`.
1. `pkill -f` sends SIGTERM, then a wait loop of up to 20 s runs. These lines are unchanged.
2. If `pgrep -d,` still finds a match (the `if` condition is exempt from `-e`), the block runs:
   - it prints the marker line;
   - it runs `ps -o … -p "$pids"`, where a comma-separated list is valid input for procps `ps`, followed by `|| true`;
   - it runs `pkill -9 … || true`;
   - it waits up to 5 s;
   - if a match remains, the final `pgrep` fails the step with exit 1.
3. When SIGTERM works, the condition is false and the step prints nothing extra.

**Checker.**
- `job_steps` → `_block_scalar` removes the block indentation, so the inner lines keep a 2-space prefix and the closing line is a bare `fi`.
- `ci_lines` skips the new `# CI-only:` comment.
- `compare` drops the `(step, line)` pairs found in `CI_ONLY`, then checks that each entry is matched exactly once.
- So the 7 new entries match only in Guide 8. The bare `fi` entry is scoped to Guide 8, so a `fi` in another job or step is not hidden by it.

**Seams:**
- The "CI-only: runserver log" step runs only on `if: failure()` (lines 334–336).
- No later step uses port 8000 or starts runserver again.
- `pgrep -f` does not match the step's own shell. Its command line is the temp-file path, and `pgrep` excludes itself.

##### 3. Verification (what I ran myself)

These are development checks on `34211ef`, in this container. They are not CI.

| Check | Result |
|---|---|
| `python3 -I scripts/check_install_guide.py` (Python 3.13.18) | `install guide check OK: 23 commands match in order (allow-listed: 10 guide-only lines, 31 CI-only lines)`, exit 0. Matches the spec's claim. |
| `pytest -q tests/ci/test_install_guide_check.py` on a `git archive` copy of `34211ef` (`uv run --no-project --isolated --python python3 --with pytest`) | **47 passed** (plus 1 config warning, because pytest-django is not installed) |
| The same on `905ca51` | **12 failed**, 35 passed. Matches the claimed red state. |
| The stop block taken from the workflow at `34211ef`, run with `bash --noprofile --norc -e -o pipefail`, against a dummy `manage.py runserver` that ignores SIGTERM | Printed the marker line and a `ps` row (PID, PPID, `S`, `00:21`, cmd). Bash reported `Killed`. Exit 0 after 20 s. No process left. |

**The 12 new tests use the real path.** They:
- run `check.job_steps` and `check.ci_lines` on the real workflow;
- delete each fallback line in turn (7 parametrized cases) and expect "not used". Edits stay inside the fallback block, so they never touch the bare `fi` of `postgresql-tdd`;
- put the old stop check back and expect it to be rejected;
- move `pkill -9` to Guide 9 and expect the error to name Guide 9;
- duplicate the whole block and expect "more than once".

**CI at the time of review:** run [43604169369](https://github.com/porntaned/ERP-for-Factory/actions/runs/43604169369) was still `in_progress` for `install-guide` and `postgresql-tdd`. So the owner's merge criterion (all 3 checks passing on the PR page) is **not verified by this review**.

##### 4. Findings (by severity; all low or info)

1. **Low: if the fallback fires, nothing on the PR page shows it.** Location: `.github/workflows/foundation.yml:310`.
   - **Why it matters:** When the step recovers through `pkill -9`, it passes. The marker and the `ps` output appear only inside the step log. The runserver log step runs only on failure, so the server log from that moment is not printed either. The purpose of the "C" part of the ruling (collect evidence about the cause) depends on someone opening a green job's log.
   - **Evidence:** the `if: failure()` at line 335, and my local run above, which exits 0 after printing the marker.
   - **Smallest change:** prefix the marker with `::warning::` so a passing run carries an annotation. Optionally add `cat runserver.log || true` inside the block, with the matching allow-list entry. Under the owner's rule 1 (low/info findings are recorded as limits without asking), this can be recorded as a known limit instead of being changed.

2. **Info: the root cause is still unknown.** Location: spec, "Known limits".
   - AGENTS.md asks for root causes to be diagnosed. The owner chose to collect evidence with A + C instead, and the spec states this openly. It is acceptable under that ruling and is recorded for completeness.

3. **Info: the checker does not enforce the order of CI-only lines.** Location: `scripts/check_install_guide.py`, `compare`.
   - It matches CI-only lines per step as a set. Only `test_r2_guide_8_ends_with_the_stop_lines_in_order` pins their order, and only for the current workflow file.
   - This existed before this round and is documented in the spec's known limits. No change needed.

4. **Info: the spec's claims match what I observed.** These all agree:
   - the line counts (22 CI-only lines in Guide 8, 31 in total);
   - the test counts (12 failed and 35 passed on `905ca51`; 47 passed on `1922d9a`);
   - the `cmp` byte offset (7436).

   `34211ef` is documentation only, as stated: it touches only `docs/assignments/i119-install-guide-check.md`.

I found no correctness defects in the diff.

##### Verdict

**ship.** The change does exactly what the owner ruled. It touches only the Guide 8 CI-only lines and their allow-list, and it is tested on the real path. I reproduced the fallback, the red and green test results, and the checker output. All findings are low or info and can be recorded as limits under the owner's rule 1. Merging still depends on the owner's criterion, all 3 checks passing on the PR page, which was not met yet when I reviewed (CI still running).

### Manager disposition (re-review 2; Manager session, 2026-11-14)

All findings are low or info; per the owner's standing rule 1 ([comment 6878167755](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878167755)) and the round-2 ruling ([comment 6878538215](https://github.com/porntaned/ERP-for-Factory/issues/119#issuecomment-6878538215)) they are recorded as known limits without asking; no code change.

| # | Disposition |
|---|---|
| 1 | **Known limit:** when the `pkill -9` fallback fires, the step passes and the marker and `ps` output appear only in the `install-guide` step log (no PR annotation; the runserver log step runs only on failure). Whoever checks a run must open the "Guide 8" log and look for `runserver did not stop after SIGTERM; fallback: pkill -9`. |
| 2 | **Known limit:** the root cause of the stuck processes (runs #293 attempt 1 and #296) is still unknown; the fallback prints `ps` evidence when it happens. |
| 3 | **Known limit** (already in the spec): CI-only lines are matched per step without order; the stop lines' order is pinned only by a test. |
| 4 | Informational; no action. |

CI for head `34211ef`, run [#297](https://github.com/porntaned/ERP-for-Factory/actions/runs/43604169369): `install-guide` passed on attempt 1, and its "Guide 8" log does **not** contain the fallback marker (SIGTERM stopped runserver; `pkill -9` was not used).
