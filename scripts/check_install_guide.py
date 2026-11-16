"""Check that docs/INSTALL.md and the CI job `install-guide` run the same commands (Issue #119).

Guide side: every line inside the ```bash blocks of docs/INSTALL.md, in order; a `#` line there is
an error (owner ruling D4). CI side: every line of every `run:` of the job `install-guide` of
.github/workflows/foundation.yml, in step order; `#` lines are skipped (D4). The workflow is read
as text with the standard library (D3). After removing the allow-listed lines below (D2 (a)), the
two sequences must be equal, character for character and in order.

Repair round 1 (review findings 1-3, owner comment 6843916308): every allow-list entry matches
exactly once; each guide-only line sits right before the compared command its entry names, in the
order of the list; step names in the job are unique; a ```sh or ```shell block in the guide fails.

Standard library only; runs on Python 3.12 (the runner's python3) and 3.14.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB = "install-guide"

# The compared guide commands that the guide-only lines must come right before (finding 1).
BEFORE_PSQL = "psql -d postgres -tAc 'SHOW server_version'"
BEFORE_SED = 'sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$ERP_SECRET_KEY|" \\'
BEFORE_RESET = "uv run --env-file .env python manage.py seed_production_demo --reset"

# Lines in the guide that the job does not run, as line: (reason, the compared command that must
# come next in the guide). The guide must have them exactly once each, in this order (finding 1).
# Each cites its item of the M7.2 `# CI-only:` list (docs/assignments/m72-install-guide.md). Items 1
# (setup-uv) and 3 (service superuser) change no command line and need no entry.
ITEM_2, ITEM_4, ITEM_5 = "M7.2 CI-only item 2", "M7.2 CI-only item 4", "M7.2 CI-only item 5"
GUIDE_ONLY = {
    # Item 2: the job `env` replaces the seven `export` lines of guide step 2.
    "export PGHOST=127.0.0.1": (ITEM_2, BEFORE_PSQL),
    "export PGPORT=5432": (ITEM_2, BEFORE_PSQL),
    "export PGUSER=postgres": (ITEM_2, BEFORE_PSQL),
    "export PGPASSWORD='replace-with-your-superuser-password'": (ITEM_2, BEFORE_PSQL),
    "export ERP_DB_PASSWORD='replace-with-a-local-db-password'": (ITEM_2, BEFORE_PSQL),
    'export ERP_SECRET_KEY="$(openssl rand -hex 32)"': (ITEM_2, BEFORE_PSQL),
    "export ERP_DEMO_PASSWORD='replace-with-a-demo-password'": (ITEM_2, BEFORE_PSQL),
    # Item 4: actions/checkout replaces `git clone` and `cd` of guide step 4.
    "git clone https://github.com/porntaned/ERP-for-Factory.git": (ITEM_4, BEFORE_SED),
    "cd ERP-for-Factory": (ITEM_4, BEFORE_SED),
    # Item 5: the job runs runserver in the background instead (see CI_ONLY).
    "DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver": (ITEM_5, BEFORE_RESET),
}

GUIDE_8 = "Guide 8: Run and log in"
SEED_RERUN = "CI-only: rerunning the seeds adds nothing"

# Lines the job runs that the guide does not, as (step name, exact line): a line is allowed only in
# the step named here, so the seed-rerun step cannot hide a repeated command in another step. Each
# entry must match exactly once (finding 2).
CI_ONLY = {
    # Item 5: runserver in the background, HTTP checks, then stopped and checked to be stopped.
    (
        GUIDE_8,
        "DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver"
        " > runserver.log 2>&1 &",
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "for i in $(seq 1 30); do curl -fsS -o /dev/null http://127.0.0.1:8000/accounts/login/"
        " && break; sleep 1; done",
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "code=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/accounts/login/)",
    ): "M7.2 CI-only item 5",
    (GUIDE_8, 'echo "login page: $code"; test "$code" = 200'): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "curl -sS -c cookies.txt -b cookies.txt -o /dev/null http://127.0.0.1:8000/accounts/login/",
    ): "M7.2 CI-only item 5",
    (GUIDE_8, "csrf=$(awk '$6 == \"csrftoken\" {print $7}' cookies.txt)"): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "code=$(curl -sS -c cookies.txt -b cookies.txt -o /dev/null -w '%{http_code}' \\",
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        '  --data-urlencode "csrfmiddlewaretoken=$csrf"'
        ' --data-urlencode "username=demo-warehouse" \\',
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        '  --data-urlencode "password=$ERP_DEMO_PASSWORD" http://127.0.0.1:8000/accounts/login/)',
    ): "M7.2 CI-only item 5",
    (GUIDE_8, 'echo "login POST: $code"; test "$code" = 302'): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "curl -sS -b cookies.txt -o balance.html http://127.0.0.1:8000/",
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "grep -F '<span class=\"navbar-text me-3\">demo-warehouse</span>' balance.html",
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        'grep -F \'<td>LED-CHIP</td><td>L-0001</td><td>RM-A</td><td class="text-end">100</td>'
        "<td>RELEASED</td>' balance.html",
    ): "M7.2 CI-only item 5",
    (GUIDE_8, "pkill -f 'manage.py runserver'"): "M7.2 CI-only item 5",
    # Finding 6 (owner comment 6877846545): wait up to 20 s for it to stop (was `sleep 2`).
    (
        GUIDE_8,
        "for i in $(seq 1 20); do pgrep -f 'manage.py runserver' > /dev/null || break;"
        " sleep 1; done",
    ): "M7.2 CI-only item 5",
    # Repair round 2 (run #296; owner comment 6878538215): still running after the 20 s wait →
    # show its processes, pkill -9, wait up to 5 s; fail only if it is still running after that.
    # Replaces `if pgrep … echo "runserver still running"; exit 1; fi`.
    (GUIDE_8, "if pids=$(pgrep -d, -f 'manage.py runserver'); then"): "M7.2 CI-only item 5",
    # Issue #126 P4: the echo is a GitHub warning annotation, shown on the run's summary page.
    (
        GUIDE_8,
        '  echo "::warning title=install-guide::runserver did not stop after SIGTERM;'
        ' fallback: pkill -9"',
    ): "M7.2 CI-only item 5",
    (GUIDE_8, '  ps -o pid,ppid,stat,etime,cmd -p "$pids" || true'): "M7.2 CI-only item 5",
    (GUIDE_8, "  pkill -9 -f 'manage.py runserver' || true"): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "  for i in $(seq 1 5); do pgrep -f 'manage.py runserver' > /dev/null || break;"
        " sleep 1; done",
    ): "M7.2 CI-only item 5",
    (
        GUIDE_8,
        "  if pgrep -f 'manage.py runserver'; then"
        ' echo "runserver still running after pkill -9"; exit 1; fi',
    ): "M7.2 CI-only item 5",
    (GUIDE_8, "fi"): "M7.2 CI-only item 5",
    # Item 6: the extra step reruns both seeds and diffs per-model row counts.
    (
        SEED_RERUN,
        "count='from django.apps import apps;"
        " [print(m._meta.label, m.objects.count()) for m in apps.get_models()]'",
    ): "M7.2 CI-only item 6",
    (
        SEED_RERUN,
        'uv run --env-file .env python manage.py shell -c "$count" > counts-before.txt',
    ): "M7.2 CI-only item 6",
    (SEED_RERUN, "uv run --env-file .env python manage.py seed_demo"): "M7.2 CI-only item 6",
    (
        SEED_RERUN,
        "uv run --env-file .env python manage.py seed_production_demo",
    ): "M7.2 CI-only item 6",
    (
        SEED_RERUN,
        'uv run --env-file .env python manage.py shell -c "$count" > counts-after.txt',
    ): "M7.2 CI-only item 6",
    (SEED_RERUN, "cat counts-after.txt"): "M7.2 CI-only item 6",
    (SEED_RERUN, "diff counts-before.txt counts-after.txt"): "M7.2 CI-only item 6",
    # Item 7: the `if: failure()` step prints the server log.
    ("CI-only: runserver log", "cat runserver.log || true"): "M7.2 CI-only item 7",
    # Owner ruling D1: this script's own call line.
    (
        "CI-only: guide and job commands match",
        "python3 scripts/check_install_guide.py",
    ): "owner ruling D1",
}


class CheckError(Exception):
    """The guide and the job differ, or a file cannot be read as expected."""


# Fences whose commands the check would not read (finding 3): a guide command goes in ```bash.
REJECTED_FENCES = {"sh", "shell"}


def guide_lines(text):
    """Return (line number, line) for every line inside a ```bash block, in order."""
    lines = []
    in_block = False
    for number, line in enumerate(text.split("\n"), start=1):
        if not in_block:
            in_block = line.strip() == "```bash"
            stripped = line.strip()
            info = stripped[3:].split()[:1] if stripped[:3] in ("```", "~~~") else []
            if info and info[0].lower() in REJECTED_FENCES:
                raise CheckError(
                    f"INSTALL.md line {number}: a {stripped[:3]}{info[0]} block; guide commands"
                    f" go in ```bash blocks, the only ones this check reads: {line}"
                )
        elif line.strip() == "```":
            in_block = False
        elif line.lstrip().startswith("#"):
            raise CheckError(f"INSTALL.md line {number}: a `#` line inside a bash block: {line}")
        else:
            lines.append((number, line))
    if in_block:
        raise CheckError("docs/INSTALL.md: a ```bash block is not closed")
    if not lines:
        raise CheckError("docs/INSTALL.md: no ```bash block found")
    return lines


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _is_content(line):
    """True for a line that is neither blank nor a YAML comment."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _section(lines, start, indent):
    """Return the index after the last line that belongs to the key at `lines[start - 1]`."""
    end = start
    while end < len(lines) and (not _is_content(lines[end]) or _indent(lines[end]) > indent):
        end += 1
    return end


def _first_content(lines, start, end, what):
    for index in range(start, end):
        if _is_content(lines[index]):
            return index
    raise CheckError(f"workflow: {what} not found")


def _job_body(lines, job):
    """Return (start, end) of the lines of `job` under the top-level `jobs:` key."""
    if "jobs:" not in lines:
        raise CheckError("workflow: top-level `jobs:` not found")
    start = lines.index("jobs:") + 1
    end = _section(lines, start, 0)
    job_indent = _indent(lines[_first_content(lines, start, end, "any job")])
    header = " " * job_indent + job + ":"
    for index in range(start, end):
        if lines[index].rstrip() == header:
            return index + 1, _section(lines, index + 1, job_indent)
    raise CheckError(f"workflow: job `{job}:` not found under `jobs:`")


def _steps_body(lines, start, end, job):
    first = _first_content(lines, start, end, f"the keys of job `{job}`")
    key = " " * _indent(lines[first]) + "steps:"
    for index in range(start, end):
        if lines[index].rstrip() == key:
            return index + 1, _section(lines, index + 1, _indent(lines[first]))
    raise CheckError(f"workflow: `steps:` of job `{job}` not found")


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _block_scalar(lines, start, key_indent):
    """Return the lines of a `|` block scalar starting at `start`, de-indented, clip-chomped."""
    content = []
    block_indent = None
    for line in lines[start:]:
        if not line.strip():
            content.append("")
            continue
        if block_indent is None:
            block_indent = _indent(line)
        if block_indent <= key_indent or _indent(line) < block_indent:
            break
        content.append(line[block_indent:])
    while content and not content[-1]:
        content.pop()
    return content


def _run_lines(step_name, value, lines, start, key_indent):
    """Return the command lines of one `run:` value, or raise for a form this check cannot read."""
    if value == "|":
        commands = _block_scalar(lines, start, key_indent)
    elif value and value[0] not in "|>\"'&*!" and " #" not in value:
        commands = [value]
    else:
        raise CheckError(f"workflow: step `{step_name}`: unsupported `run:` form: run: {value}")
    if not commands:
        raise CheckError(f"workflow: step `{step_name}`: `run:` has no command lines")
    return commands


def _parse_step(lines, start, end):
    """Return (name, run lines or None) of the step whose `- ` item spans lines[start:end]."""
    item_indent = _indent(lines[start])
    key_indent = item_indent + 2
    step = [" " * key_indent + lines[start][key_indent:]] + lines[start + 1 : end]
    name, run_value, run_at = None, None, None
    for offset, line in enumerate(step):
        if not _is_content(line) or _indent(line) != key_indent:
            continue
        key, _, value = line.strip().partition(":")
        if key == "name":
            name = _unquote(value.strip())
        elif key == "run":
            run_value, run_at = value.strip(), start + offset + 1
    name = name or f"(unnamed step at workflow line {start + 1})"
    if run_value is None:
        return name, None
    return name, _run_lines(name, run_value, lines, run_at, key_indent)


def job_steps(text, job=JOB):
    """Return (step name, run lines) of every step of `job` that has a `run:`, in order."""
    lines = text.split("\n")
    job_start, job_end = _job_body(lines, job)
    start, end = _steps_body(lines, job_start, job_end, job)
    first = _first_content(lines, start, end, f"a step of job `{job}`")
    item = " " * _indent(lines[first]) + "- "
    starts = [i for i in range(start, end) if lines[i].startswith(item)]
    seen = {}
    steps = []
    for index, step_start in enumerate(starts):
        step_end = starts[index + 1] if index + 1 < len(starts) else end
        name, commands = _parse_step(lines, step_start, step_end)
        if name in seen:
            raise CheckError(
                f"workflow: job `{job}`: step name `{name}` is used by more than one step"
                f" (workflow lines {seen[name]} and {step_start + 1})"
            )
        seen[name] = step_start + 1
        if commands is not None:
            steps.append((name, commands))
    if not steps:
        raise CheckError(f"workflow: `run:` not found in job `{job}`")
    return steps


def ci_lines(steps):
    """Return (step name, line) for every run line, skipping `#` lines (D4)."""
    return [
        (name, line)
        for name, commands in steps
        for line in commands
        if not line.lstrip().startswith("#")
    ]


def _show_guide(entry):
    if entry is None:
        return "guide: (end of the guide's commands)"
    return f"guide: {entry[1]}    [INSTALL.md line {entry[0]}]"


def _show_ci(entry):
    if entry is None:
        return "job:   (end of the job's commands)"
    return f"job:   {entry[1]}    [step `{entry[0]}`]"


def _next_text(line):
    return "(end of the guide's commands)" if line is None else line


def _check_guide_only_places(guide):
    """Each guide-only line must come right before the compared command its entry names, in the
    order of GUIDE_ONLY (finding 1). Call after the exactly-once check."""
    found, pending = [], []
    for number, line in guide:
        if line in GUIDE_ONLY:
            pending.append((number, line))
        else:
            found += [(n, only, line) for n, only in pending]
            pending = []
    found += [(n, only, None) for n, only in pending]
    expected = [(line, before) for line, (_, before) in GUIDE_ONLY.items()]
    for (number, line, before), (want, want_before) in zip(found, expected):
        if (line, before) != (want, want_before):
            raise CheckError(
                "guide-only lines are not where the allow-list puts them; first difference:\n"
                f"  expected: {want}    (next compared command: {_next_text(want_before)})\n"
                f"  found:    {line}    [INSTALL.md line {number}]"
                f" (next compared command: {_next_text(before)})"
            )


def compare(guide, ci):
    """Compare guide lines with CI lines after the allow-lists; return the success summary."""
    kept_guide = [entry for entry in guide if entry[1] not in GUIDE_ONLY]
    kept_ci = [entry for entry in ci if entry not in CI_ONLY]
    for index in range(max(len(kept_guide), len(kept_ci))):
        g = kept_guide[index] if index < len(kept_guide) else None
        c = kept_ci[index] if index < len(kept_ci) else None
        if g is None or c is None or g[1] != c[1]:
            raise CheckError(
                f"first difference at compared command {index} (0-based):\n"
                f"  {_show_guide(g)}\n  {_show_ci(c)}"
            )
    guide_seen = Counter(line for _, line in guide if line in GUIDE_ONLY)
    ci_seen = Counter(entry for entry in ci if entry in CI_ONLY)
    unused = [line for line in GUIDE_ONLY if not guide_seen[line]]
    unused += [f"step `{step}`: {line}" for step, line in CI_ONLY if not ci_seen[(step, line)]]
    if unused:
        raise CheckError("allow-list entries not used:\n  " + "\n  ".join(unused))
    repeated = [
        f"{line}: {count} times [INSTALL.md lines "
        + ", ".join(str(n) for n, other in guide if other == line)
        + "]"
        for line, count in guide_seen.items()
        if count > 1
    ]
    repeated += [
        f"step `{step}`: {line}: {count} times"
        for (step, line), count in ci_seen.items()
        if count > 1
    ]
    if repeated:
        raise CheckError(
            "allow-list entries matched more than once (each must match exactly once):\n  "
            + "\n  ".join(repeated)
        )
    _check_guide_only_places(guide)
    return (
        f"OK: {len(kept_guide)} commands match in order"
        f" (allow-listed: {len(guide) - len(kept_guide)} guide-only lines,"
        f" {len(ci) - len(kept_ci)} CI-only lines)"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check docs/INSTALL.md against the CI job.")
    parser.add_argument("--guide", type=Path, default=ROOT / "docs" / "INSTALL.md")
    parser.add_argument(
        "--workflow", type=Path, default=ROOT / ".github" / "workflows" / "foundation.yml"
    )
    args = parser.parse_args(argv)
    try:
        guide = guide_lines(args.guide.read_text(encoding="utf-8"))
        ci = ci_lines(job_steps(args.workflow.read_text(encoding="utf-8")))
        summary = compare(guide, ci)
    except (CheckError, OSError, UnicodeDecodeError) as error:
        print(f"install guide check FAILED: {error}", file=sys.stderr)
        return 1
    print(f"install guide check {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
