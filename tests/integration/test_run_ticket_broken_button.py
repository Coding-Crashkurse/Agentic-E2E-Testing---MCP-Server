from __future__ import annotations

import pytest

from e2e_verifier.application.store import ArtifactNames
from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.enums import (
    CriterionStatus,
    ErrorCategory,
    HighlightSource,
    Outcome,
    RunMode,
    StepStatus,
    Verdict,
)
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.server.app import ServerFactory
from tests.conftest import TicketFactory

pytestmark = pytest.mark.integration


async def test_broken_button_is_reproduced_with_highlight(
    settings: Settings, pool: BrowserPool, tickets: TicketFactory
) -> None:
    factory = ServerFactory(settings, pool)
    options = RunOptions(mode=RunMode.REPRODUCE, failure_hold_ms=300, post_roll_ms=200)
    plan = factory.compiler.compile(tickets.broken_button(), options)
    location = factory.store.create_run()
    result = await factory.runner.run(plan, location.run_id, location.path)

    assert result.outcome is Outcome.CRITERIA_NOT_MET
    assert result.verdict is Verdict.REPRODUCED
    statuses = {step.id: step.status for step in result.steps}
    assert statuses == {
        "__open__": StepStatus.PASSED,
        "s1": StepStatus.PASSED,
        "s2": StepStatus.FAILED,
        "s3": StepStatus.SKIPPED,
    }
    failed = result.first_failure()
    assert failed is not None
    assert failed.error is not None
    assert failed.error.category is ErrorCategory.ASSERTION
    assert failed.error.highlight_target is not None
    assert failed.error.highlight_target.source is HighlightSource.PREVIOUS_ACTION
    assert failed.error.highlight_target.step_id == "s1"
    assert failed.error.highlight_target.rect is not None
    assert failed.error.highlight_target.rect.width > 0
    assert failed.failure_screenshot is not None
    assert (location.path / failed.failure_screenshot).is_file()
    assert result.observations.requests_after_step["s1"] == 0
    criteria = {criterion.id: criterion.status for criterion in result.acceptance_criteria}
    assert criteria == {"AC1": CriterionStatus.NOT_MET, "AC2": CriterionStatus.UNKNOWN}
    assert "Bug reproduced" in result.summary
    report = (location.path / ArtifactNames.REPORT).read_text(encoding="utf-8")
    assert "**reproduced**" in report
    assert (location.path / ArtifactNames.VIDEO).is_file()


async def test_verify_mode_reports_still_broken(
    settings: Settings, pool: BrowserPool, tickets: TicketFactory
) -> None:
    factory = ServerFactory(settings, pool)
    options = RunOptions(mode=RunMode.VERIFY, failure_hold_ms=0, post_roll_ms=0)
    plan = factory.compiler.compile(tickets.broken_button(), options)
    location = factory.store.create_run()
    result = await factory.runner.run(plan, location.run_id, location.path)
    assert result.verdict is Verdict.STILL_BROKEN
