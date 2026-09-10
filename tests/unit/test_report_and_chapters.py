from __future__ import annotations

from e2e_verifier.application.chapters import ChapterWriter
from e2e_verifier.application.compiler import ExecutionPlan, PlanCompiler
from e2e_verifier.application.report import ReportBuilder, format_offset
from e2e_verifier.domain.result import RunResult
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import BugTicket


def plan_for(result: RunResult) -> ExecutionPlan:
    ticket = BugTicket.model_validate(
        {
            "id": result.ticket_id,
            "title": result.title,
            "url": result.target_url,
            "steps": [
                {"id": "s1", "action": "fill", "target": {"label": "Name"}, "value": "Anna"},
                {"id": "s2", "action": "click", "target": {"test_id": "save"}},
                {"id": "s3", "action": "expect_visible", "target": {"test_id": "toast"}},
            ],
            "expected": "toast",
            "actual": "nothing",
            "acceptance_criteria": [{"id": "AC1", "description": "toast", "step_ids": ["s3"]}],
        }
    )
    return PlanCompiler(Settings(_env_file=None)).compile(ticket, None)


def test_format_offset() -> None:
    assert format_offset(None) == "-"
    assert format_offset(1720) == "00:01.7"
    assert format_offset(65_432) == "01:05.4"


def test_report_contains_all_sections(sample_result: RunResult) -> None:
    plan = plan_for(sample_result)
    report = ReportBuilder().build(sample_result, plan)
    assert report.startswith("# WEB-142 - Save button does nothing")
    for heading in (
        "## Summary",
        "## Acceptance criteria",
        "## Steps",
        "## Observations",
        "## Artifacts",
        "## Input",
    ):
        assert heading in report
    assert "| AC1 | toast | not_met |" in report
    assert "| 3 | Expect toast | failed | 00:01.7 | 5024 ms |" in report
    assert "Requests after step s2: 0" in report
    assert "Expected: toast" in report
    assert "trace.zip" in report


def test_chapters_are_valid_webvtt(sample_result: RunResult) -> None:
    vtt = ChapterWriter().build(sample_result)
    lines = vtt.splitlines()
    assert lines[0] == "WEBVTT"
    assert "00:00:01.240 --> 00:00:01.512" in vtt
    assert "[failed] Expect toast" in vtt
    assert vtt.count("-->") == 3


def test_chapters_skip_steps_without_offsets(sample_result: RunResult) -> None:
    steps = [step.model_copy(update={"started_offset_ms": None}) for step in sample_result.steps]
    vtt = ChapterWriter().build(sample_result.model_copy(update={"steps": steps}))
    assert "-->" not in vtt
