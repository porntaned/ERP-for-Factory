"""Write a Markdown CI evidence summary from a pytest JUnit XML report.

The session that develops this repository cannot download GitHub Actions log text, but
it can read comments through the REST API. CI therefore posts this summary as a commit
comment (push) and a single updated PR comment (pull_request). Usage:

    python scripts/ci_summary.py reports/junit.xml > ci-summary.md
"""

import os
import platform
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MARKER = "<!-- erp-ci-summary -->"


def parse_junit(path: Path) -> dict | None:
    if not path.is_file():
        return None
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    for suite in suites:
        for key in ("tests", "failures", "errors", "skipped"):
            totals[key] += int(suite.get(key, 0))
        totals["time"] += float(suite.get("time", 0))
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    return totals


def server_version() -> str:
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import django

        django.setup()
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            return cursor.fetchone()[0]
    except Exception as exc:  # evidence helper: report, never hide the real job result
        return f"unavailable ({type(exc).__name__})"


def render(totals: dict | None, env: dict, postgres: str) -> str:
    run_url = f"{env.get('GITHUB_SERVER_URL', '')}/{env.get('GITHUB_REPOSITORY', '')}"
    run_url += f"/actions/runs/{env.get('GITHUB_RUN_ID', '')}"
    lines = [
        MARKER,
        "### CI evidence",
        "",
        f"- Commit: `{env.get('GITHUB_SHA', 'unknown')}`",
        f"- Event: `{env.get('GITHUB_EVENT_NAME', 'unknown')}` · "
        f"Run [#{env.get('GITHUB_RUN_NUMBER', '?')}]({run_url})",
        f"- Job status: **{env.get('JOB_STATUS', 'unknown')}**",
        f"- PostgreSQL: `{postgres}` · Python: `{platform.python_version()}`",
    ]
    if totals is None:
        lines.append("- Tests: no JUnit report (the job stopped before the full suite ran)")
    else:
        lines.append(
            f"- Last pytest step (the full suite when every step passed): "
            f"**{totals['passed']} passed**, {totals['failures']} failed, "
            f"{totals['errors']} errors, {totals['skipped']} skipped, "
            f"{totals['tests']} total in {totals['time']:.2f}s"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    report = Path(argv[1]) if len(argv) > 1 else Path("reports/junit.xml")
    sys.stdout.write(render(parse_junit(report), dict(os.environ), server_version()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
