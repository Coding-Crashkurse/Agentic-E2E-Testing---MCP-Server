from __future__ import annotations

import json
import zipfile

import pytest

from e2e_verifier.application.store import ArtifactNames
from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.server.app import ServerFactory
from tests.conftest import TicketFactory

pytestmark = pytest.mark.integration


async def test_trace_contains_step_groups_and_video_matches_steps(
    settings: Settings, pool: BrowserPool, tickets: TicketFactory
) -> None:
    factory = ServerFactory(settings, pool)
    plan = factory.compiler.compile(
        tickets.happy(), RunOptions(failure_hold_ms=0, post_roll_ms=200, record_har=True)
    )
    location = factory.store.create_run()
    result = await factory.runner.run(plan, location.run_id, location.path)

    with zipfile.ZipFile(location.path / ArtifactNames.TRACE) as archive:
        blob = b"".join(
            archive.read(name) for name in archive.namelist() if name.endswith(".trace")
        )
    for planned in plan.steps:
        encoded = json.dumps(planned.trace_group)[1:-1].encode("utf-8")
        assert encoded in blob, planned.trace_group

    assert result.artifacts.har == ArtifactNames.HAR
    assert (location.path / ArtifactNames.HAR).stat().st_size > 0

    last = result.steps[-1]
    assert last.ended_offset_ms is not None
    video = location.path / ArtifactNames.VIDEO
    assert video.stat().st_size > 0
    assert result.duration_ms >= last.ended_offset_ms
    assert result.artifacts.video == ArtifactNames.VIDEO
    assert (location.path / ArtifactNames.CONSOLE).is_file()
    network = (location.path / ArtifactNames.NETWORK).read_text(encoding="utf-8")
    assert "/api/settings" in network
