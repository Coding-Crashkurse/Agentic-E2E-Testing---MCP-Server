from __future__ import annotations

import pytest

from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import Scenario
from e2e_verifier.server.app import ServerFactory
from tests.conftest import FixtureSite

pytestmark = pytest.mark.integration


async def test_probe_reports_reachable_site(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    result = await factory.probe.probe(f"{fixture_site.base_url}/index.html")
    assert result.reachable
    assert result.status == 200
    assert result.title == "Fixture App"
    assert result.load_time_ms is not None
    assert result.console_errors == []


async def test_probe_reports_unreachable_port(settings: Settings, pool: BrowserPool) -> None:
    factory = ServerFactory(settings, pool)
    result = await factory.probe.probe("http://127.0.0.1:9/")
    assert not result.reachable
    assert result.error is not None


async def test_discover_finds_save_button_with_test_id(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    result = await factory.discovery.discover(
        f"{fixture_site.base_url}/index.html", "Save", None, 10
    )
    assert result.candidates
    save = next(candidate for candidate in result.candidates if candidate.test_id == "save")
    assert save.role == "button"
    assert save.name == "Save"
    assert save.visible
    assert save.suggested_target.test_id == "save"
    assert "button" in result.aria_snapshot
    assert not result.aria_snapshot_truncated


async def test_discover_runs_steps_before(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    steps = [{"id": "nav", "action": "click", "target": {"test_id": "nav-settings"}}]
    parsed = Scenario.model_validate(
        {"id": "x", "title": "x", "url": fixture_site.base_url, "steps": steps}
    ).steps
    result = await factory.discovery.discover(
        f"{fixture_site.base_url}/index.html", "Home", parsed, 10
    )
    assert result.final_url.endswith("/settings.html")
    assert any(candidate.test_id == "nav-home" for candidate in result.candidates)
