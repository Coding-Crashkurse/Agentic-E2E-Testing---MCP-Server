from __future__ import annotations

import pytest

from e2e_verifier.browser.session import BrowserPool, BrowserSession
from e2e_verifier.domain.enums import StepPhase, StepStatus
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import Target
from e2e_verifier.domain.ticket import Scenario
from e2e_verifier.server.app import ServerFactory
from tests.conftest import FixtureSite

pytestmark = pytest.mark.integration

BANNER_TITLE = "Zebra step title unlikely to appear on the page"


def scenario(base_url: str) -> Scenario:
    return Scenario.model_validate(
        {
            "id": "hud",
            "title": "hud",
            "url": f"{base_url}/index.html",
            "steps": [
                {"id": "open", "action": "goto", "url": "/index.html"},
                {"id": "top", "action": "click", "target": {"test_id": "top-button"}},
                {
                    "id": "toast",
                    "action": "expect_text",
                    "target": {"test_id": "toast"},
                    "text": "Top clicked",
                },
                {"id": "nav", "action": "goto", "url": "/settings.html"},
            ],
        }
    )


async def test_hud_state_frame_and_click_through(
    settings: Settings,
    pool: BrowserPool,
    fixture_site: FixtureSite,
) -> None:
    factory = ServerFactory(settings, pool)
    plan = factory.compiler.compile(scenario(fixture_site.base_url), RunOptions())
    session = factory.sessions.create(plan, None, light=False)
    assert isinstance(session, BrowserSession)
    await session.open()
    try:
        open_step, top_step, toast_step, nav_step = plan.steps
        assert (await session.execute(open_step, 0)).status is StepStatus.PASSED

        await session.hud.set_step(1, 4, BANNER_TITLE, StepPhase.STEPS)
        state = await session.hud.get_state()
        assert state is not None
        assert state["step"]["title"] == BANNER_TITLE
        assert await session.page.get_by_text(BANNER_TITLE).count() == 0
        assert await session.page.locator("e2e-hud").count() == 1

        assert (await session.execute(top_step, 0)).status is StepStatus.PASSED
        assert (await session.execute(toast_step, 0)).status is StepStatus.PASSED

        rect = await session.highlight_rect(Target(test_id="delete"))
        assert rect is not None
        await session.hud.mark_failure(rect, "boom")
        state = await session.hud.get_state()
        assert state is not None
        assert state["step"]["status"] == "failed"
        assert state["failure"]["rect"]["width"] == pytest.approx(rect.width)
        assert state["failure"]["message"] == "boom"

        assert (await session.execute(nav_step, 0)).status is StepStatus.PASSED
        state = await session.hud.get_state()
        assert state is not None
        assert state["step"]["title"] == BANNER_TITLE
        assert state["failure"]["message"] == "boom"
    finally:
        closed = await session.close()
    assert closed.warnings == []


async def test_hud_can_be_disabled(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    options = RunOptions(hud={"enabled": False})
    plan = factory.compiler.compile(scenario(fixture_site.base_url), options)
    session = factory.sessions.create(plan, None, light=False)
    await session.open()
    try:
        assert (await session.execute(plan.steps[0], 0)).status is StepStatus.PASSED
        assert isinstance(session, BrowserSession)
        assert await session.page.locator("e2e-hud").count() == 0
    finally:
        await session.close()
