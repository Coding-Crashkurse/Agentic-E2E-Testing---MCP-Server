from __future__ import annotations

import zipfile

import pytest

from e2e_verifier.application.store import ArtifactNames
from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.enums import Outcome, StepStatus, Verdict
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.server.app import ServerFactory
from tests.conftest import TicketFactory

pytestmark = pytest.mark.integration

MIN_VIDEO_BYTES = 10_000


async def test_happy_path_produces_video_trace_and_verdict(
    settings: Settings, pool: BrowserPool, tickets: TicketFactory
) -> None:
    factory = ServerFactory(settings, pool)
    ticket = tickets.happy()
    plan = factory.compiler.compile(ticket, RunOptions(failure_hold_ms=0, post_roll_ms=300))
    location = factory.store.create_run()
    result = await factory.runner.run(plan, location.run_id, location.path)

    assert result.outcome is Outcome.CRITERIA_MET, result.model_dump_json(indent=2)
    assert result.verdict is Verdict.FIXED
    assert all(step.status is StepStatus.PASSED for step in result.steps)
    assert result.warnings == []

    run_dir = location.path
    video = run_dir / ArtifactNames.VIDEO
    assert video.is_file()
    assert video.stat().st_size > MIN_VIDEO_BYTES
    assert not (run_dir / ArtifactNames.VIDEO_RAW).exists()

    trace = run_dir / ArtifactNames.TRACE
    assert trace.is_file()
    with zipfile.ZipFile(trace) as archive:
        names = archive.namelist()
        assert any(name.endswith(".trace") for name in names)
        assert any(name.startswith("resources/") for name in names)

    shots = sorted((run_dir / ArtifactNames.SCREENSHOTS).glob("*.png"))
    assert len(shots) == len(result.steps)
    assert (run_dir / ArtifactNames.CHAPTERS).read_text(encoding="utf-8").count("-->") == len(
        result.steps
    )
    assert result.observations.requests_after_step["s2"] >= 1
    assert result.observations.console_errors == 0
    assert factory.store.read_result(location.run_id).verdict is Verdict.FIXED
