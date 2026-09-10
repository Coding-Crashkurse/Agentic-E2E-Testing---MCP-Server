from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager, nullcontext
from pathlib import Path
from typing import Any

import pytest

from e2e_verifier.application.clock import SystemClock
from e2e_verifier.application.compiler import ExecutionPlan, PlanCompiler, PlannedStep
from e2e_verifier.application.ports import ClosedSession, ProbeNavigation, SessionObservations
from e2e_verifier.application.runner import ScenarioRunner
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.domain.enums import (
    AnnotationTone,
    ErrorCategory,
    HighlightSource,
    Outcome,
    RunMode,
    StepPhase,
    StepStatus,
    Verdict,
)
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import BrowserInfo, NetworkEntry, Rect, StepOutcome
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import Target
from e2e_verifier.domain.ticket import BugTicket, Viewport


class FakeHud:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def set_step(self, index: int, total: int, title: str, phase: StepPhase) -> None:
        self.calls.append(("set_step", index))

    async def mark_success(self) -> None:
        self.calls.append(("mark_success", None))

    async def mark_failure(self, rect: Rect | None, message: str) -> None:
        self.calls.append(("mark_failure", rect))

    async def mark_error(self, message: str) -> None:
        self.calls.append(("mark_error", message))

    async def set_final(self, verdict: Verdict, message: str) -> None:
        self.calls.append(("set_final", verdict))

    async def annotate(self, rect: Rect | None, message: str, tone: AnnotationTone) -> None:
        self.calls.append(("annotate", (rect, message, tone)))

    async def clear_annotation(self) -> None:
        self.calls.append(("clear_annotation", None))


class FakeSession:
    def __init__(self, plan: ExecutionPlan, script: dict[str, StepOutcome], delay_s: float) -> None:
        self.plan = plan
        self.script = script
        self.delay_s = delay_s
        self.hud = FakeHud()
        self.clock = SystemClock()
        self.origin = 0
        self.closed = False
        self.executed: list[str] = []
        self.network: list[NetworkEntry] = []

    async def open(self) -> None:
        self.origin = self.clock.monotonic_ms()

    def offset_ms(self) -> int:
        return self.clock.monotonic_ms() - self.origin

    async def trace_group(self, name: str) -> AbstractAsyncContextManager[Any]:
        return nullcontext()

    async def execute(self, planned: PlannedStep, window_start_ms: int) -> StepOutcome:
        self.executed.append(planned.step.id)
        await asyncio.sleep(self.delay_s)
        if planned.step.id == "s1":
            self.network.append(
                NetworkEntry(
                    offset_ms=self.offset_ms(), phase="request", method="POST", url="http://x/api"
                )
            )
        return self.script.get(planned.step.id, StepOutcome.passed())

    async def highlight_rect(self, target: Target) -> Rect | None:
        if target.test_id == "save":
            return Rect(x=10, y=20, width=30, height=40)
        return None

    async def screenshot(self, path: Path, full_page: bool) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")

    async def screenshot_bytes(self, full_page: bool, jpeg_quality: int | None) -> bytes:
        return b"jpeg" if jpeg_quality is not None else b"png"

    async def page_title(self) -> str:
        return "Fake page"

    async def close(self) -> ClosedSession:
        self.closed = True
        return ClosedSession(
            browser=BrowserInfo(name="chromium", version="1", headless=True, viewport=Viewport())
        )

    def observations(self) -> SessionObservations:
        return SessionObservations(network=list(self.network))

    def current_url(self) -> str:
        return "http://x/"

    async def navigate_probe(self, url: str, timeout_ms: int) -> ProbeNavigation:
        return ProbeNavigation(status=200, final_url=url, title="t", load_time_ms=1)

    async def aria_snapshot(self) -> str:
        return ""

    async def discover(self, query: str | None, max_results: int) -> list[dict[str, Any]]:
        return []


class FakeSessionFactory:
    def __init__(self, script: dict[str, StepOutcome], delay_s: float = 0.0) -> None:
        self.script = script
        self.delay_s = delay_s
        self.sessions: list[FakeSession] = []

    def create(self, plan: ExecutionPlan, run_dir: Path | None, light: bool = False) -> FakeSession:
        session = FakeSession(plan, self.script, self.delay_s)
        self.sessions.append(session)
        return session


def ticket() -> BugTicket:
    return BugTicket.model_validate(
        {
            "id": "T-9",
            "title": "runner test",
            "url": "http://localhost/",
            "steps": [
                {"id": "s1", "action": "click", "target": {"test_id": "save"}},
                {"id": "s2", "action": "expect_visible", "target": {"test_id": "toast"}},
                {"id": "s3", "action": "expect_no_console_errors"},
            ],
            "expected": "x",
            "acceptance_criteria": [
                {"id": "AC1", "description": "toast", "step_ids": ["s2"]},
                {"id": "AC2", "description": "clean", "step_ids": ["s3"]},
            ],
        }
    )


def build(
    tmp_path: Path, factory: FakeSessionFactory, **settings_overrides: Any
) -> tuple[ScenarioRunner, ArtifactStore]:
    settings = Settings(_env_file=None, artifact_dir=tmp_path, **settings_overrides)
    store = ArtifactStore(settings.artifact_dir)
    return ScenarioRunner(factory, store, SystemClock(), settings), store


async def run(
    tmp_path: Path,
    factory: FakeSessionFactory,
    options: RunOptions | None = None,
    **settings_overrides: Any,
) -> tuple[Any, ArtifactStore, Path]:
    runner, store = build(tmp_path, factory, **settings_overrides)
    plan = PlanCompiler(Settings(_env_file=None, **settings_overrides)).compile(ticket(), options)
    location = store.create_run()
    result = await runner.run(plan, location.run_id, location.path)
    return result, store, location.path


async def test_happy_path_writes_all_artifacts(tmp_path: Path) -> None:
    factory = FakeSessionFactory({})
    result, store, run_dir = await run(
        tmp_path, factory, RunOptions(failure_hold_ms=0, post_roll_ms=0)
    )
    assert result.outcome is Outcome.CRITERIA_MET
    assert result.verdict is Verdict.FIXED
    assert [step.status for step in result.steps] == [StepStatus.PASSED] * 4
    for name in (
        ArtifactNames.RESULT,
        ArtifactNames.REPORT,
        ArtifactNames.CHAPTERS,
        ArtifactNames.CONSOLE,
        ArtifactNames.NETWORK,
        ArtifactNames.TICKET,
        ArtifactNames.OPTIONS,
    ):
        assert (run_dir / name).is_file(), name
    assert len(result.artifacts.screenshots) == 4
    assert result.observations.requests_after_step["s1"] == 1
    assert store.read_result(result.run_id).run_id == result.run_id
    session = factory.sessions[0]
    assert session.closed
    assert session.hud.calls[-1][0] == "set_final"


async def test_failure_highlights_previous_action_and_skips_rest(tmp_path: Path) -> None:
    script = {"s2": StepOutcome.failed(ErrorCategory.ASSERTION, "toast missing")}
    factory = FakeSessionFactory(script)
    options = RunOptions(mode=RunMode.REPRODUCE, failure_hold_ms=0, post_roll_ms=0)
    result, _, _ = await run(tmp_path, factory, options)
    assert result.verdict is Verdict.REPRODUCED
    statuses = {step.id: step.status for step in result.steps}
    assert statuses["s2"] is StepStatus.FAILED
    assert statuses["s3"] is StepStatus.SKIPPED
    failed = result.first_failure()
    assert failed is not None
    assert failed.error is not None
    assert failed.error.highlight_target is not None
    assert failed.error.highlight_target.source is HighlightSource.PREVIOUS_ACTION
    assert failed.error.highlight_target.step_id == "s1"
    assert failed.error.highlight_target.rect == Rect(x=10, y=20, width=30, height=40)
    assert failed.failure_screenshot is not None
    hud = factory.sessions[0].hud
    names = [call[0] for call in hud.calls]
    assert names.index("mark_failure") < names.index("set_final")
    assert factory.sessions[0].executed == ["__open__", "s1", "s2"]


async def test_continue_on_failure_runs_remaining_steps(tmp_path: Path) -> None:
    script = {"s2": StepOutcome.failed(ErrorCategory.ASSERTION, "toast missing")}
    factory = FakeSessionFactory(script)
    options = RunOptions(continue_on_failure=True, failure_hold_ms=0, post_roll_ms=0)
    result, _, _ = await run(tmp_path, factory, options)
    assert factory.sessions[0].executed == ["__open__", "s1", "s2", "s3"]
    assert result.verdict is Verdict.STILL_BROKEN
    assert result.acceptance_criteria[1].status == "met"


async def test_precondition_failure_becomes_error(tmp_path: Path) -> None:
    script = {"__open__": StepOutcome.failed(ErrorCategory.NAVIGATION, "refused")}
    factory = FakeSessionFactory(script)
    result, _, _ = await run(tmp_path, factory, RunOptions(failure_hold_ms=0, post_roll_ms=0))
    assert result.outcome is Outcome.ERROR
    assert result.verdict is Verdict.INCONCLUSIVE
    first = result.steps[0]
    assert first.status is StepStatus.ERROR
    assert first.error is not None
    assert first.error.category is ErrorCategory.PRECONDITION
    assert factory.sessions[0].hud.calls[-1][0] == "set_final"


async def test_run_timeout_marks_current_step_and_still_writes_result(tmp_path: Path) -> None:
    factory = FakeSessionFactory({}, delay_s=3.0)
    result, _, run_dir = await run(
        tmp_path,
        factory,
        RunOptions(run_timeout_s=5, failure_hold_ms=0, post_roll_ms=0),
        default_run_timeout_s=5,
    )
    assert result.outcome is Outcome.ERROR
    assert result.run_error is not None
    assert result.run_error.category is ErrorCategory.RUN_TIMEOUT
    errored = [step for step in result.steps if step.status is StepStatus.ERROR]
    assert len(errored) == 1
    assert (run_dir / ArtifactNames.RESULT).is_file()
    assert factory.sessions[0].closed


@pytest.mark.parametrize("mode", [RunMode.VERIFY, RunMode.REPRODUCE])
async def test_secret_values_are_masked_in_messages(tmp_path: Path, mode: RunMode) -> None:
    factory = FakeSessionFactory({"s2": StepOutcome.failed(ErrorCategory.ASSERTION, "saw hunter2")})
    settings = Settings(_env_file=None, artifact_dir=tmp_path)
    store = ArtifactStore(settings.artifact_dir)
    runner = ScenarioRunner(factory, store, SystemClock(), settings)
    source = ticket().model_copy(
        update={
            "steps": [
                *ticket().steps[:1],
                *BugTicket.model_validate(
                    {
                        **ticket().model_dump(by_alias=True),
                        "url": "http://localhost/",
                        "steps": [
                            {
                                "id": "s2",
                                "action": "fill",
                                "target": {"label": "pw"},
                                "value": "hunter2",
                                "secret": True,
                            },
                            {"id": "s3", "action": "expect_no_console_errors"},
                        ],
                        "acceptance_criteria": [
                            {"id": "AC2", "description": "clean", "step_ids": ["s3"]}
                        ],
                    }
                ).steps,
            ],
            "acceptance_criteria": [ticket().acceptance_criteria[1]],
        }
    )
    plan = PlanCompiler(settings).compile(
        source, RunOptions(mode=mode, failure_hold_ms=0, post_roll_ms=0)
    )
    location = store.create_run()
    result = await runner.run(plan, location.run_id, location.path)
    assert "hunter2" not in result.model_dump_json()
    assert "hunter2" not in (location.path / ArtifactNames.REPORT).read_text(encoding="utf-8")
