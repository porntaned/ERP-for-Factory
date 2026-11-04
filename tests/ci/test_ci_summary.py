"""The CI evidence summary parses JUnit totals and never hides a missing report."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = spec_from_file_location("ci_summary", ROOT / "scripts" / "ci_summary.py")
ci_summary = module_from_spec(spec)
spec.loader.exec_module(ci_summary)

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="10" failures="1" errors="1" skipped="2"
time="3.50"></testsuite></testsuites>"""


def test_parses_totals(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(JUNIT)
    totals = ci_summary.parse_junit(report)
    assert totals == {
        "tests": 10,
        "failures": 1,
        "errors": 1,
        "skipped": 2,
        "time": 3.5,
        "passed": 6,
    }


def test_render_contains_marker_sha_and_counts(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(JUNIT)
    env = {"GITHUB_SHA": "abc123", "GITHUB_RUN_NUMBER": "7", "JOB_STATUS": "failure"}
    body = ci_summary.render(ci_summary.parse_junit(report), env, "18.6")
    assert body.startswith(ci_summary.MARKER)
    assert "`abc123`" in body and "**6 passed**, 1 failed" in body and "`18.6`" in body
    assert "**failure**" in body


def test_missing_report_is_stated(tmp_path):
    body = ci_summary.render(ci_summary.parse_junit(tmp_path / "none.xml"), {}, "18.6")
    assert "no JUnit report" in body


def test_pull_request_shows_head_and_tested_merge():
    env = {"GITHUB_SHA": "merge1", "HEAD_SHA": "head1"}
    body = ci_summary.render(None, env, "18.6")
    assert "`head1` (PR head; tested as merge `merge1`)" in body
