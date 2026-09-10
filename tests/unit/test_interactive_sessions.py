from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from e2e_verifier.application.clock import SystemClock
from e2e_verifier.application.compiler import PlanCompiler
from e2e_verifier.application.finalize import RunFinalizer
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.interactive import SessionManager
from e2e_verifier.application.registry import RunRegistry
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.domain.enums import AnnotationTone, ErrorCategory, StepStatus, Verdict
from e2e_verifier.domain.errors import (
    HostNotAllowedError,
    SessionNotFoundError,
    TooManySessionsError,
)
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import StepOutcome
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import ClickStep, ExpectVisibleStep, Target
from tests.unit.test_runner_with_fake_session import FakeSessionFactory


def build(tmp_path: Path, factory: FakeSessionFactory, **overrides: Any) -> SessionManager:
    settings = Settings(_env_file=None, artifact_dir=tmp_path, **overrides)
    store = ArtifactStore(settings.artifact_dir)
    clock = SystemClock()
    return SessionManager(
        sessions=factory,
        compiler=PlanCompiler(settings),
        store=store,
        registry=RunRegistry(store),
        finalizer=RunFinalizer(store, clock, settings),
        clock=clock,
        settings=settings,
        allowlist=HostAllowlist(["localhost"]),
    )


async def test_open_act_annotate_close_produces_artifacts(tmp_path: Path) -> None:
    factory = FakeSessionFactory({"a2": StepOutcome.failed(ErrorCategory.ASSERTION, "no toast")})
    manager = build(tmp_path, factory)
    session, first = await manager.open("http://localhost/", RunOptions(post_roll_ms=0))
    assert first.step.status is StepStatus.PASSED
    assert first.step.action == "goto"
    assert session.info().steps_executed == 1

    clicked = await session.act(ClickStep(id="a1", target=Target(test_id="save")))
    assert clicked.step.status is StepStatus.PASSED
    failed = await session.act(ExpectVisibleStep(id="a2", target=Target(test_id="toast")))
    assert failed.step.status is StepStatus.FAILED
    assert failed.step.error is not None
    assert failed.step.error.highlight_target is not None
    assert failed.step.error.highlight_target.step_id == "a1"
    assert failed.hint is not None

    note = await session.annotate("looks wrong", Target(test_id="save"), AnnotationTone.FAILURE, 0)
    assert note.rect is not None
    assert note.screenshot is not None
    hud_calls = [call[0] for call in factory.sessions[0].hud.calls]
    assert "annotate" in hud_calls

    duplicate = await session.act(ClickStep(id="a1", target=Target(test_id="save")))
    assert duplicate.step.id == "a1_2"

    result = await manager.close(session.session_id, None, None)
    assert result.run_id == session.session_id
    assert result.verdict is Verdict.FAILED
    assert [step.id for step in result.steps] == ["open", "a1", "a2", "a1_2"]
    assert (session.run_dir / ArtifactNames.RESULT).is_file()
    assert (session.run_dir / ArtifactNames.REPORT).is_file()
    assert len(result.artifacts.screenshots) == 5
    assert factory.sessions[0].closed
    with pytest.raises(SessionNotFoundError):
        manager.get(session.session_id)


async def test_verdict_and_summary_override(tmp_path: Path) -> None:
    manager = build(tmp_path, FakeSessionFactory({}))
    session, _ = await manager.open("http://localhost/", RunOptions(post_roll_ms=0))
    result = await manager.close(session.session_id, Verdict.REPRODUCED, "agent says so")
    assert result.verdict is Verdict.REPRODUCED
    assert result.summary == "agent says so"


async def test_limits_and_allowlist(tmp_path: Path) -> None:
    manager = build(tmp_path, FakeSessionFactory({}), max_sessions=1)
    with pytest.raises(HostNotAllowedError):
        await manager.open("http://evil.test/", None)
    session, _ = await manager.open("http://localhost/", RunOptions(post_roll_ms=0))
    with pytest.raises(TooManySessionsError):
        await manager.open("http://localhost/", None)
    assert [info.session_id for info in manager.list_open()] == [session.session_id]
    await manager.close_all()
    assert manager.list_open() == []


async def test_idle_sessions_are_reaped(tmp_path: Path) -> None:
    manager = build(tmp_path, FakeSessionFactory({}), session_idle_timeout_s=30)
    session, _ = await manager.open("http://localhost/", RunOptions(post_roll_ms=0))
    session._last_activity_ms -= 31_000
    reaped = await manager.reap_idle()
    assert reaped == [session.session_id]
    assert manager.list_open() == []
    assert (session.run_dir / ArtifactNames.RESULT).is_file()
