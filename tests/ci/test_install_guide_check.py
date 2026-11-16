"""The commands of docs/INSTALL.md and of the CI job install-guide stay identical (Issue #119).

No database. Every failure case is built from the real files with a small text edit; the real files
are never changed.
"""

import re
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("check_install_guide", ROOT / "scripts" / "check_install_guide.py")
check = module_from_spec(spec)
spec.loader.exec_module(check)

GUIDE = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "foundation.yml").read_text(encoding="utf-8")

SEED_STEP = "CI-only: rerunning the seeds adds nothing"


def edit(text, old, new, count=1):
    """Replace `old` by `new`, after checking `old` occurs exactly `count` times."""
    assert text.count(old) == count, f"{old!r} occurs {text.count(old)} times, expected {count}"
    return text.replace(old, new)


def run(tmp_path, capsys, guide=GUIDE, workflow=WORKFLOW):
    guide_path = tmp_path / "INSTALL.md"
    workflow_path = tmp_path / "foundation.yml"
    guide_path.write_text(guide, encoding="utf-8")
    workflow_path.write_text(workflow, encoding="utf-8")
    code = check.main(["--guide", str(guide_path), "--workflow", str(workflow_path)])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def assert_fails(tmp_path, capsys, *expected, guide=GUIDE, workflow=WORKFLOW):
    code, output = run(tmp_path, capsys, guide=guide, workflow=workflow)
    assert code == 1, output
    assert "FAILED" in output
    for text in expected:
        assert text in output, output
    return output


# The real files


def test_real_files_pass(tmp_path, capsys):
    code, output = run(tmp_path, capsys)
    assert code == 0, output
    assert output.count("\n") == 1, "the success summary is one line"
    assert re.search(r"OK: \d+ commands match", output), output


def test_real_files_pass_with_default_paths(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # the default paths do not depend on the working directory
    assert check.main([]) == 0, capsys.readouterr()


def test_real_job_is_read_step_by_step():
    steps = dict(check.job_steps(WORKFLOW, "install-guide"))
    assert steps["Guide 1: What you need"] == ["git --version", "uv --version"]
    # one-line run:
    assert steps["CI-only: runserver log"] == ["cat runserver.log || true"]
    # continuation lines keep their own indentation after the block indentation is removed
    assert steps["Guide 4: Write .env"][1] == (
        '  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$ERP_DB_PASSWORD|" \\'
    )
    # `# CI-only:` comment lines inside a run: block are read, then skipped for the comparison (D4)
    guide_8 = "Guide 8: Run and log in"
    assert any(line.startswith("# CI-only:") for line in steps[guide_8])
    compared = [line for step, line in check.ci_lines(steps.items()) if step == guide_8]
    assert compared and not any(line.lstrip().startswith("#") for line in compared)
    # only the install-guide job is read
    assert "uv run ruff check ." not in [line for lines in steps.values() for line in lines]


def test_real_guide_lines_are_the_bash_blocks():
    lines = [line for _, line in check.guide_lines(GUIDE)]
    assert lines[:2] == ["git --version", "uv --version"]
    assert "CREATE DATABASE erp_factory OWNER erp_factory;" in lines
    assert not any("Ctrl+C" in line for line in lines)  # prose is not read


def test_every_allow_list_entry_has_a_reason():
    guide_reasons = {"M7.2 CI-only item 2", "M7.2 CI-only item 4", "M7.2 CI-only item 5"}
    ci_reasons = {
        "M7.2 CI-only item 5",
        "M7.2 CI-only item 6",
        "M7.2 CI-only item 7",
        "owner ruling D1",
    }
    assert check.GUIDE_ONLY and check.CI_ONLY
    assert {reason for reason, _ in check.GUIDE_ONLY.values()} <= guide_reasons
    assert set(check.CI_ONLY.values()) <= ci_reasons
    real_steps = {name for name, _ in check.job_steps(WORKFLOW, "install-guide")}
    assert {step for step, _ in check.CI_ONLY} <= real_steps


def test_pkill_9_fallback_shows_a_warning_annotation():
    """Issue #126 P4: if the fallback runs, the run's summary page shows a GitHub warning."""
    guide_8 = dict(check.job_steps(WORKFLOW, "install-guide"))["Guide 8: Run and log in"]
    fallback = [line for line in guide_8 if "fallback: pkill -9" in line]
    assert fallback == [
        '  echo "::warning title=install-guide::runserver did not stop after SIGTERM;'
        ' fallback: pkill -9"'
    ]


# Failure cases (a)-(i) of the spec


def test_a_guide_command_changed_by_one_character(tmp_path, capsys):
    guide = edit(GUIDE, "uv sync --locked --all-groups\n", "uv sync --locked --all-group\n")
    assert_fails(
        tmp_path,
        capsys,
        "guide: uv sync --locked --all-group",
        "job:   uv sync --locked --all-groups",
        guide=guide,
    )


def test_b_job_command_changed(tmp_path, capsys):
    workflow = edit(
        WORKFLOW,
        "          uv run --env-file .env python manage.py migrate\n",
        "          uv run --env-file .env python manage.py migrat\n",
    )
    assert_fails(
        tmp_path,
        capsys,
        "guide: uv run --env-file .env python manage.py migrate",
        "job:   uv run --env-file .env python manage.py migrat",
        workflow=workflow,
    )


def test_c_job_line_not_in_allow_list(tmp_path, capsys):
    workflow = edit(
        WORKFLOW,
        "          uv run --env-file .env python manage.py migrate\n",
        "          uv run --env-file .env python manage.py migrate\n"
        "          uv run --env-file .env python manage.py flush --noinput\n",
    )
    assert_fails(
        tmp_path,
        capsys,
        "job:   uv run --env-file .env python manage.py flush --noinput",
        workflow=workflow,
    )


def test_d_guide_line_removed(tmp_path, capsys):
    guide = edit(GUIDE, "uv run python --version\n", "")
    assert_fails(tmp_path, capsys, "job:   uv run python --version", guide=guide)


def test_d_last_guide_line_removed(tmp_path, capsys):
    last = (
        "printf '%s\\n' \"$ERP_DEMO_PASSWORD\" | uv run --env-file .env python manage.py "
        "set_demo_passwords --password-stdin\n```\n\nThe flush"
    )
    guide = edit(GUIDE, last, "```\n\nThe flush")
    assert_fails(tmp_path, capsys, "guide: (end of the guide's commands)", guide=guide)


def test_e_two_lines_swapped(tmp_path, capsys):
    check_line = "uv run --env-file .env python manage.py check\n"
    migrate_line = "uv run --env-file .env python manage.py migrate\n"
    guide = edit(GUIDE, check_line + migrate_line, migrate_line + check_line)
    assert_fails(
        tmp_path,
        capsys,
        "guide: uv run --env-file .env python manage.py migrate",
        "job:   uv run --env-file .env python manage.py check",
        guide=guide,
    )


@pytest.mark.parametrize("side", ["guide", "job"])
def test_f_sql_heredoc_differs(tmp_path, capsys, side):
    line = "CREATE DATABASE erp_factory OWNER erp_factory;"
    changed = "CREATE DATABASE erp_factory OWNER postgres;"
    guide, workflow = GUIDE, WORKFLOW
    if side == "guide":
        guide = edit(GUIDE, line, changed)
    else:
        workflow = edit(WORKFLOW, line, changed)
    assert_fails(tmp_path, capsys, changed, guide=guide, workflow=workflow)


@pytest.mark.parametrize("comment", ["# check the tools", "  # check the tools"])
def test_g_hash_line_inside_a_guide_bash_block(tmp_path, capsys, comment):
    guide = edit(GUIDE, "```bash\ngit --version\n", f"```bash\n{comment}\ngit --version\n")
    number = guide.split("\n").index(comment) + 1
    assert_fails(tmp_path, capsys, f"INSTALL.md line {number}:", "`#`", comment, guide=guide)


def test_h_job_missing(tmp_path, capsys):
    workflow = edit(WORKFLOW, "\n  install-guide:\n", "\n  install-guide-renamed:\n")
    assert_fails(tmp_path, capsys, "install-guide", "not found", workflow=workflow)


MINIMAL_JOB = """name: Foundation
jobs:
  install-guide:
    runs-on: ubuntu-24.04
    steps:
      - name: "Guide 4: Get the code"
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
"""


def test_h_job_without_run_lines(tmp_path, capsys):
    assert_fails(tmp_path, capsys, "run:", "not found", workflow=MINIMAL_JOB)


def test_h_job_without_steps(tmp_path, capsys):
    workflow = "jobs:\n  install-guide:\n    runs-on: ubuntu-24.04\n"
    assert_fails(tmp_path, capsys, "steps:", "not found", workflow=workflow)


def test_h_empty_run_block(tmp_path, capsys):
    workflow = MINIMAL_JOB + '      - name: "Guide 1: What you need"\n        run: |\n\n'
    assert_fails(tmp_path, capsys, "Guide 1: What you need", "run:", workflow=workflow)


def test_h_unsupported_run_form(tmp_path, capsys):
    workflow = (
        MINIMAL_JOB + '      - name: "Guide 1: What you need"\n        run: >-\n          x\n'
    )
    assert_fails(tmp_path, capsys, "Guide 1: What you need", "run:", workflow=workflow)


def test_i_ci_only_line_in_another_step(tmp_path, capsys):
    pkill = "          pkill -f 'manage.py runserver'\n"
    reset = "          uv run --env-file .env python manage.py seed_production_demo --reset\n"
    workflow = edit(WORKFLOW, reset, pkill + reset)
    assert_fails(
        tmp_path,
        capsys,
        "job:   pkill -f 'manage.py runserver'",
        "Guide 9: Start the demo data again",
        workflow=workflow,
    )


def test_i_seed_rerun_lines_only_allowed_in_their_step(tmp_path, capsys):
    workflow = edit(WORKFLOW, f'- name: "{SEED_STEP}"', '- name: "Guide 7b: seeds again"')
    assert_fails(tmp_path, capsys, "Guide 7b: seeds again", workflow=workflow)


def test_unused_allow_list_entry_fails(tmp_path, capsys):
    guide = edit(GUIDE, "cd ERP-for-Factory\n", "")
    assert_fails(tmp_path, capsys, "cd ERP-for-Factory", "not used", guide=guide)


# Repair round 1 (Issue #119 review findings 1-3; owner comment 6843916308)

CD_LINE = "cd ERP-for-Factory\n"
SED_LINE = 'sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$ERP_SECRET_KEY|" \\\n'
ENV_EXAMPLE_LINE = "  .env.example > .env\n"


def test_1_guide_only_line_moved_to_a_new_block_at_the_end(tmp_path, capsys):
    # Reviewer probe P2.
    guide = edit(GUIDE, CD_LINE, "") + "\n```bash\ncd ERP-for-Factory\n```\n"
    assert_fails(
        tmp_path, capsys, "not where the allow-list puts them", "cd ERP-for-Factory", guide=guide
    )


def test_1_guide_only_line_moved_after_a_compared_line(tmp_path, capsys):
    guide = edit(GUIDE, CD_LINE + SED_LINE, SED_LINE)
    guide = edit(guide, ENV_EXAMPLE_LINE, ENV_EXAMPLE_LINE + CD_LINE)
    assert_fails(
        tmp_path, capsys, "not where the allow-list puts them", "cd ERP-for-Factory", guide=guide
    )


def test_1_guide_only_lines_swapped(tmp_path, capsys):
    clone = "git clone https://github.com/porntaned/ERP-for-Factory.git\n"
    guide = edit(GUIDE, clone + CD_LINE, CD_LINE + clone)
    assert_fails(
        tmp_path, capsys, "not where the allow-list puts them", "cd ERP-for-Factory", guide=guide
    )


def test_1_guide_only_runserver_line_moved_before_migrate(tmp_path, capsys):
    runserver = "DJANGO_DEBUG=true uv run --env-file .env python manage.py runserver\n"
    migrate = "uv run --env-file .env python manage.py migrate\n"
    guide = edit(edit(GUIDE, runserver, ""), migrate, runserver + migrate)
    assert_fails(
        tmp_path,
        capsys,
        "not where the allow-list puts them",
        "(next compared command: uv run --env-file .env python manage.py migrate)",
        guide=guide,
    )


def test_1_guide_only_line_duplicated(tmp_path, capsys):
    port = "export PGPORT=5432\n"
    guide = edit(GUIDE, port, port + port)
    assert_fails(tmp_path, capsys, "more than once", "export PGPORT=5432", guide=guide)


def test_2_ci_only_line_duplicated_in_its_own_step(tmp_path, capsys):
    # Reviewer probe P10.
    seed = "          uv run --env-file .env python manage.py seed_production_demo\n"
    after = (
        '          uv run --env-file .env python manage.py shell -c "$count" > counts-after.txt\n'
    )
    workflow = edit(WORKFLOW, seed + after, seed + seed + after)
    assert_fails(
        tmp_path,
        capsys,
        "more than once",
        f"step `{SEED_STEP}`: uv run --env-file .env python manage.py seed_production_demo",
        workflow=workflow,
    )


def test_2_ci_only_stop_line_duplicated(tmp_path, capsys):
    pkill = "          pkill -f 'manage.py runserver'\n"
    workflow = edit(WORKFLOW, pkill, pkill + pkill)
    assert_fails(
        tmp_path, capsys, "more than once", "pkill -f 'manage.py runserver'", workflow=workflow
    )


def test_2_duplicate_step_name_before_write_env(tmp_path, capsys):
    # Reviewer probe P8: a second "Guide 8" step could run Guide 8's allow-listed lines anywhere.
    write_env = '      - name: "Guide 4: Write .env"\n'
    extra = (
        "      - name: \"Guide 8: Run and log in\"\n        run: pkill -f 'manage.py runserver'\n\n"
    )
    workflow = edit(WORKFLOW, write_env, extra + write_env)
    assert_fails(
        tmp_path, capsys, "Guide 8: Run and log in", "more than one step", workflow=workflow
    )


def test_2_duplicate_step_name_of_compared_steps(tmp_path, capsys):
    workflow = edit(
        WORKFLOW,
        '- name: "Guide 9: Start the demo data again"',
        '- name: "Guide 7: Load the demo data"',
    )
    assert_fails(
        tmp_path, capsys, "Guide 7: Load the demo data", "more than one step", workflow=workflow
    )


@pytest.mark.parametrize("info", ["sh", "shell"])
def test_3_sh_or_shell_block_in_the_guide(tmp_path, capsys, info):
    guide = GUIDE + f"\n```{info}\nuv run --env-file .env python manage.py flush --noinput\n```\n"
    number = guide.split("\n").index(f"```{info}") + 1
    assert_fails(tmp_path, capsys, f"INSTALL.md line {number}:", f"```{info}", guide=guide)


def test_3_other_fences_are_not_rejected(tmp_path, capsys):
    # Only sh and shell are rejected (owner ruling); a text block is prose output, not commands.
    code, output = run(tmp_path, capsys, guide=GUIDE + "\n```text\nSystem check\n```\n")
    assert code == 0, output


# Repair round 2 (Issue #119, run #296; owner comment 6878538215): when runserver is still running
# after the 20 s wait, show its processes, then pkill -9; fail only if it is still running after that.

GUIDE_8 = "Guide 8: Run and log in"
OLD_STOP_CHECK = (
    "if pgrep -f 'manage.py runserver'; then echo \"runserver still running\"; exit 1; fi"
)
FALLBACK_LINES = [
    "if pids=$(pgrep -d, -f 'manage.py runserver'); then",
    '  echo "runserver did not stop after SIGTERM; fallback: pkill -9"',
    '  ps -o pid,ppid,stat,etime,cmd -p "$pids" || true',
    "  pkill -9 -f 'manage.py runserver' || true",
    "  for i in $(seq 1 5); do pgrep -f 'manage.py runserver' > /dev/null || break; sleep 1; done",
    "  if pgrep -f 'manage.py runserver'; then"
    ' echo "runserver still running after pkill -9"; exit 1; fi',
    "fi",
]
STOP_LINES = [
    "pkill -f 'manage.py runserver'",
    "for i in $(seq 1 20); do pgrep -f 'manage.py runserver' > /dev/null || break; sleep 1; done",
    *FALLBACK_LINES,
]
WORKFLOW_FALLBACK = "".join(f"          {line}\n" for line in FALLBACK_LINES)


def test_r2_guide_8_ends_with_the_stop_lines_in_order():
    compared = [
        line
        for step, line in check.ci_lines(check.job_steps(WORKFLOW, "install-guide"))
        if step == GUIDE_8
    ]
    assert compared[-len(STOP_LINES) :] == STOP_LINES
    assert OLD_STOP_CHECK not in compared


def test_r2_stop_lines_are_allow_listed_in_guide_8_only():
    for line in STOP_LINES:
        assert check.CI_ONLY.get((GUIDE_8, line)) == "M7.2 CI-only item 5", line
        assert [step for step, other in check.CI_ONLY if other == line] == [GUIDE_8], line
    assert (GUIDE_8, OLD_STOP_CHECK) not in check.CI_ONLY


@pytest.mark.parametrize("line", FALLBACK_LINES)
def test_r2_fallback_line_removed_from_the_job(tmp_path, capsys, line):
    # Edited inside the fallback block: a bare `fi` also ends a block of the postgresql-tdd job.
    removed = edit(WORKFLOW_FALLBACK, f"          {line}\n", "")
    workflow = edit(WORKFLOW, WORKFLOW_FALLBACK, removed)
    assert_fails(tmp_path, capsys, "not used", f"step `{GUIDE_8}`: {line}", workflow=workflow)


def test_r2_old_stop_check_alone_is_not_accepted(tmp_path, capsys):
    workflow = edit(WORKFLOW, WORKFLOW_FALLBACK, f"          {OLD_STOP_CHECK}\n")
    assert_fails(tmp_path, capsys, f"job:   {OLD_STOP_CHECK}", GUIDE_8, workflow=workflow)


def test_r2_pkill_9_moved_to_another_step(tmp_path, capsys):
    pkill_9 = "            pkill -9 -f 'manage.py runserver' || true\n"
    reset = "          uv run --env-file .env python manage.py seed_production_demo --reset\n"
    workflow = edit(edit(WORKFLOW, pkill_9, ""), reset, reset + pkill_9)
    assert_fails(
        tmp_path,
        capsys,
        "job:     pkill -9 -f 'manage.py runserver' || true",
        "Guide 9: Start the demo data again",
        workflow=workflow,
    )


def test_r2_fallback_block_duplicated(tmp_path, capsys):
    workflow = edit(WORKFLOW, WORKFLOW_FALLBACK, WORKFLOW_FALLBACK + WORKFLOW_FALLBACK)
    assert_fails(tmp_path, capsys, "more than once", "pkill -9", workflow=workflow)
