from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from pydantic import AnyHttpUrl

from e2e_verifier.application.store import ArtifactNames
from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.enums import ErrorCategory, Outcome, StepStatus
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import BugTicket
from e2e_verifier.server.app import ServerFactory
from tests.conftest import FixtureSite, TicketFactory

pytestmark = pytest.mark.integration


async def test_foreign_host_is_rejected_before_the_browser_starts(
    settings: Settings, pool: BrowserPool, tickets: TicketFactory
) -> None:
    factory = ServerFactory(settings, pool)
    ticket = tickets.happy().model_copy(update={"url": AnyHttpUrl("http://evil.example.com/")})
    async with Client(factory.build()) as client:
        with pytest.raises(ToolError, match="host_not_allowed"):
            await client.call_tool(
                "run_ticket", {"ticket": ticket.model_dump(mode="json", by_alias=True)}
            )
        assert factory.runs.count() == 0


async def test_redirect_to_foreign_host_aborts_run(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    ticket = BugTicket.model_validate(
        {
            "id": "R-1",
            "title": "redirect",
            "url": f"{fixture_site.base_url}/index.html",
            "steps": [
                {"id": "g", "action": "goto", "url": "/redirect-external"},
                {"id": "a", "action": "expect_title", "text": "Fixture"},
            ],
            "expected": "x",
            "acceptance_criteria": [{"id": "AC1", "description": "d", "step_ids": ["a"]}],
        }
    )
    plan = factory.compiler.compile(ticket, RunOptions(failure_hold_ms=0, post_roll_ms=0))
    location = factory.store.create_run()
    result = await factory.runner.run(plan, location.run_id, location.path)
    assert result.outcome is Outcome.ERROR
    goto = result.steps[0]
    assert goto.status is StepStatus.ERROR
    assert goto.error is not None
    assert goto.error.category is ErrorCategory.HOST_NOT_ALLOWED
    assert result.steps[1].status is StepStatus.SKIPPED


async def test_run_timeout_yields_error_outcome_with_artifacts(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    ticket = BugTicket.model_validate(
        {
            "id": "T-1",
            "title": "slow",
            "url": f"{fixture_site.base_url}/index.html",
            "steps": [
                {"id": "g", "action": "goto", "url": "/slow", "timeout_ms": 30_000},
                {"id": "a", "action": "expect_title", "text": "Fixture"},
            ],
            "expected": "x",
            "acceptance_criteria": [{"id": "AC1", "description": "d", "step_ids": ["a"]}],
        }
    )
    plan = factory.compiler.compile(
        ticket, RunOptions(run_timeout_s=5, failure_hold_ms=0, post_roll_ms=0)
    )
    location = factory.store.create_run()
    result = await factory.runner.run(plan, location.run_id, location.path)
    assert result.outcome is Outcome.ERROR
    assert result.run_error is not None
    assert result.run_error.category is ErrorCategory.RUN_TIMEOUT
    assert result.steps[0].status is StepStatus.ERROR
    assert (location.path / ArtifactNames.RESULT).is_file()
    assert (location.path / ArtifactNames.REPORT).is_file()
