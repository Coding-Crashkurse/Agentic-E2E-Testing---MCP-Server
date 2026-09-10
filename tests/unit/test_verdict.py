from __future__ import annotations

import pytest

from e2e_verifier.application.compiler import PlanCompiler
from e2e_verifier.application.verdict import OutcomeEvaluator, VerdictPolicy
from e2e_verifier.domain.enums import (
    CriterionStatus,
    ErrorCategory,
    Outcome,
    RunKind,
    RunMode,
    StepPhase,
    StepStatus,
    Verdict,
)
from e2e_verifier.domain.result import StepError, StepResult
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import BugTicket


@pytest.mark.parametrize(
    ("kind", "mode", "outcome", "verdict"),
    [
        (RunKind.TICKET, RunMode.VERIFY, Outcome.CRITERIA_MET, Verdict.FIXED),
        (RunKind.TICKET, RunMode.VERIFY, Outcome.CRITERIA_NOT_MET, Verdict.STILL_BROKEN),
        (RunKind.TICKET, RunMode.VERIFY, Outcome.ERROR, Verdict.INCONCLUSIVE),
        (RunKind.TICKET, RunMode.REPRODUCE, Outcome.CRITERIA_MET, Verdict.NOT_REPRODUCED),
        (RunKind.TICKET, RunMode.REPRODUCE, Outcome.CRITERIA_NOT_MET, Verdict.REPRODUCED),
        (RunKind.TICKET, RunMode.REPRODUCE, Outcome.ERROR, Verdict.INCONCLUSIVE),
        (RunKind.SCENARIO, RunMode.VERIFY, Outcome.CRITERIA_MET, Verdict.PASSED),
        (RunKind.SCENARIO, RunMode.VERIFY, Outcome.CRITERIA_NOT_MET, Verdict.FAILED),
        (RunKind.SCENARIO, RunMode.VERIFY, Outcome.ERROR, Verdict.INCONCLUSIVE),
    ],
)
def test_verdict_table(kind: RunKind, mode: RunMode, outcome: Outcome, verdict: Verdict) -> None:
    assert VerdictPolicy().decide(kind, mode, outcome) is verdict


def plan_with_two_criteria() -> tuple[PlanCompiler, BugTicket]:
    ticket = BugTicket.model_validate(
        {
            "id": "T",
            "title": "t",
            "url": "http://localhost/",
            "steps": [
                {"id": "a", "action": "click", "target": {"css": "button"}},
                {"id": "b", "action": "expect_visible", "target": {"css": ".toast"}},
                {"id": "c", "action": "expect_no_console_errors"},
            ],
            "expected": "x",
            "acceptance_criteria": [
                {"id": "AC1", "description": "toast", "step_ids": ["b"]},
                {"id": "AC2", "description": "clean", "step_ids": ["c"]},
            ],
        }
    )
    return PlanCompiler(Settings(_env_file=None)), ticket


def result(
    step_id: str, index: int, status: StepStatus, phase: StepPhase = StepPhase.STEPS
) -> StepResult:
    error = None
    if status in {StepStatus.FAILED, StepStatus.ERROR}:
        error = StepError(category=ErrorCategory.ASSERTION, message="nope")
    return StepResult(
        index=index,
        id=step_id,
        phase=phase,
        action="x",
        title=step_id,
        status=status,
        started_offset_ms=index * 100,
        ended_offset_ms=index * 100 + 50,
        error=error,
    )


def test_all_passed_means_criteria_met() -> None:
    compiler, ticket = plan_with_two_criteria()
    plan = compiler.compile(ticket, None)
    steps = [
        result("__open__", 1, StepStatus.PASSED, StepPhase.PRECONDITIONS),
        result("a", 2, StepStatus.PASSED),
        result("b", 3, StepStatus.PASSED),
        result("c", 4, StepStatus.PASSED),
    ]
    outcome, criteria = OutcomeEvaluator().evaluate(plan, steps, None)
    assert outcome is Outcome.CRITERIA_MET
    assert {criterion.status for criterion in criteria} == {CriterionStatus.MET}
    assert criteria[0].evidence is not None
    assert criteria[0].evidence.step_id == "b"


def test_failed_assertion_marks_not_met_and_skipped_unknown() -> None:
    compiler, ticket = plan_with_two_criteria()
    plan = compiler.compile(ticket, None)
    steps = [
        result("__open__", 1, StepStatus.PASSED, StepPhase.PRECONDITIONS),
        result("a", 2, StepStatus.PASSED),
        result("b", 3, StepStatus.FAILED),
        result("c", 4, StepStatus.SKIPPED),
    ]
    outcome, criteria = OutcomeEvaluator().evaluate(plan, steps, None)
    assert outcome is Outcome.CRITERIA_NOT_MET
    assert criteria[0].status is CriterionStatus.NOT_MET
    assert criteria[1].status is CriterionStatus.UNKNOWN
    assert criteria[1].evidence is None


def test_error_step_or_run_error_yields_error_outcome() -> None:
    compiler, ticket = plan_with_two_criteria()
    plan = compiler.compile(ticket, None)
    steps = [
        result("__open__", 1, StepStatus.ERROR, StepPhase.PRECONDITIONS),
        result("a", 2, StepStatus.SKIPPED),
        result("b", 3, StepStatus.SKIPPED),
        result("c", 4, StepStatus.SKIPPED),
    ]
    outcome, _ = OutcomeEvaluator().evaluate(plan, steps, None)
    assert outcome is Outcome.ERROR
    passed = [result(step.id, step.index, StepStatus.PASSED, step.phase) for step in steps]
    run_error = StepError(category=ErrorCategory.RUN_TIMEOUT, message="timeout")
    outcome, _ = OutcomeEvaluator().evaluate(plan, passed, run_error)
    assert outcome is Outcome.ERROR
