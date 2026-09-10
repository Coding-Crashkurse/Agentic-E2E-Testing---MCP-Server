from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from datetime import datetime
from pathlib import Path

from e2e_verifier.application.clock import Clock
from e2e_verifier.application.compiler import ExecutionPlan, PlannedStep
from e2e_verifier.application.finalize import FinalizeRequest, RunFinalizer
from e2e_verifier.application.ports import (
    ClosedSession,
    NullProgress,
    ProgressPort,
    SessionFactoryPort,
    SessionPort,
)
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.application.verdict import OutcomeEvaluator, SummaryComposer, VerdictPolicy
from e2e_verifier.domain.enums import (
    ErrorCategory,
    HighlightSource,
    ScreenshotMode,
    StepPhase,
    StepStatus,
)
from e2e_verifier.domain.masking import SecretMasker
from e2e_verifier.domain.result import (
    BrowserInfo,
    HighlightTarget,
    RunResult,
    StepError,
    StepOutcome,
    StepResult,
)
from e2e_verifier.domain.settings import Settings

log = logging.getLogger(__name__)

VIDEO_OFFSET_UNCERTAINTY_MS = 300
HUD_CALL_TIMEOUT_S = 3


class RunState:
    def __init__(self, plan: ExecutionPlan, run_id: str, run_dir: Path) -> None:
        self.plan = plan
        self.run_id = run_id
        self.run_dir = run_dir
        self.results: dict[int, StepResult] = {}
        self.aborted = False
        self.run_error: StepError | None = None
        self.last_action: PlannedStep | None = None
        self.window_start_ms = 0
        self.current: PlannedStep | None = None
        self.current_started_ms: int | None = None
        self.warnings: list[str] = []
        self.screenshots: list[str] = []

    def begin(self, planned: PlannedStep, offset_ms: int) -> None:
        self.current = planned
        self.current_started_ms = offset_ms

    def record(self, result: StepResult) -> None:
        self.results[result.index] = result
        self.current = None

    def note_action(self, planned: PlannedStep, started_ms: int) -> None:
        if not planned.step.is_assertion:
            self.last_action = planned
            self.window_start_ms = started_ms

    def abort(self) -> None:
        self.aborted = True

    def mark_run_timeout(self, seconds: int) -> None:
        self._mark_run_error(
            ErrorCategory.RUN_TIMEOUT, f"Run exceeded run_timeout_s={seconds} and was aborted"
        )

    def mark_crash(self, exc: BaseException) -> None:
        self._mark_run_error(ErrorCategory.INTERNAL, f"{type(exc).__name__}: {exc}")

    def ordered_results(self) -> list[StepResult]:
        return [
            self.results.get(planned.index) or self.skipped(planned) for planned in self.plan.steps
        ]

    @staticmethod
    def skipped(planned: PlannedStep) -> StepResult:
        return StepResult(
            index=planned.index,
            id=planned.step.id,
            phase=planned.phase,
            action=planned.step.action,
            title=planned.title,
            status=StepStatus.SKIPPED,
        )

    def _mark_run_error(self, category: ErrorCategory, message: str) -> None:
        self.run_error = StepError(category=category, message=message)
        self.aborted = True
        current = self.current
        if current is not None and current.index not in self.results:
            self.results[current.index] = StepResult(
                index=current.index,
                id=current.step.id,
                phase=current.phase,
                action=current.step.action,
                title=current.title,
                status=StepStatus.ERROR,
                started_offset_ms=self.current_started_ms,
                error=self.run_error,
                trace_group=current.trace_group,
            )
            self.current = None


class ScenarioRunner:
    def __init__(
        self,
        sessions: SessionFactoryPort,
        store: ArtifactStore,
        clock: Clock,
        settings: Settings,
        finalizer: RunFinalizer | None = None,
    ) -> None:
        self._sessions = sessions
        self._store = store
        self._clock = clock
        self._settings = settings
        self._finalizer = finalizer or RunFinalizer(store, clock, settings)
        self._evaluator = OutcomeEvaluator()
        self._policy = VerdictPolicy()
        self._composer = SummaryComposer()
        self._masker = SecretMasker()

    async def run(
        self,
        plan: ExecutionPlan,
        run_id: str,
        run_dir: Path,
        progress: ProgressPort | None = None,
    ) -> RunResult:
        started_at = self._clock.now()
        state = RunState(plan, run_id, run_dir)
        session = self._sessions.create(plan, run_dir)
        await self._drive(session, state, progress or NullProgress())
        closed = await self._close(session, state)
        return await self._finish(session, state, closed, started_at)

    async def _drive(self, session: SessionPort, state: RunState, progress: ProgressPort) -> None:
        options = state.plan.options
        try:
            async with asyncio.timeout(options.run_timeout_s):
                await session.open()
                await self._execute_steps(session, state, progress)
                await self._announce(session, state)
                await asyncio.sleep(options.post_roll_ms / 1000)
        except TimeoutError:
            state.mark_run_timeout(options.run_timeout_s)
            await self._quiet(session.hud.mark_error(self._run_error_message(state)))
        except Exception as exc:
            log.exception("run %s crashed", state.run_id)
            state.mark_crash(exc)
            await self._quiet(session.hud.mark_error(self._run_error_message(state)))

    async def _execute_steps(
        self, session: SessionPort, state: RunState, progress: ProgressPort
    ) -> None:
        plan = state.plan
        for planned in plan.steps:
            if state.aborted:
                state.record(state.skipped(planned))
                continue
            result = await self._run_step(session, state, planned)
            state.record(result)
            await progress.report(planned.index, plan.total, f"{planned.title}: {result.status}")

    async def _run_step(
        self, session: SessionPort, state: RunState, planned: PlannedStep
    ) -> StepResult:
        plan = state.plan
        await session.hud.set_step(planned.index, plan.total, planned.title, planned.phase)
        started = session.offset_ms()
        state.begin(planned, started)
        async with await session.trace_group(planned.trace_group):
            outcome = await session.execute(planned, state.window_start_ms)
        ended = session.offset_ms()
        state.note_action(planned, started)
        return await self._settle(session, state, planned, outcome, started, ended)

    async def _settle(
        self,
        session: SessionPort,
        state: RunState,
        planned: PlannedStep,
        outcome: StepOutcome,
        started: int,
        ended: int,
    ) -> StepResult:
        status, error = self._classify(planned, outcome, state.plan.secrets)
        result = StepResult(
            index=planned.index,
            id=planned.step.id,
            phase=planned.phase,
            action=planned.step.action,
            title=planned.title,
            status=status,
            started_offset_ms=started,
            ended_offset_ms=ended,
            error=error,
            trace_group=planned.trace_group,
        )
        if status is StepStatus.PASSED:
            return await self._settle_passed(session, state, planned, result)
        if status is StepStatus.FAILED:
            return await self._settle_failed(session, state, planned, result)
        return await self._settle_error(session, state, planned, result)

    def _classify(
        self, planned: PlannedStep, outcome: StepOutcome, secrets: list[str]
    ) -> tuple[StepStatus, StepError | None]:
        status = outcome.status
        error = outcome.error
        if error is not None:
            error = error.model_copy(
                update={"message": self._masker.mask_text(error.message, secrets)}
            )
        if status is StepStatus.FAILED and planned.phase is StepPhase.PRECONDITIONS:
            status = StepStatus.ERROR
            message = error.message if error else "precondition failed"
            error = StepError(category=ErrorCategory.PRECONDITION, message=message)
        return status, error

    async def _settle_passed(
        self, session: SessionPort, state: RunState, planned: PlannedStep, result: StepResult
    ) -> StepResult:
        await session.hud.mark_success()
        if state.plan.options.screenshots is ScreenshotMode.EACH_STEP:
            shot = await self._capture(session, state, planned, "passed", full_page=False)
            return result.model_copy(update={"screenshot": shot})
        return result

    async def _settle_failed(
        self, session: SessionPort, state: RunState, planned: PlannedStep, result: StepResult
    ) -> StepResult:
        options = state.plan.options
        highlight = await self._highlight(session, state, planned)
        error = result.error or StepError(category=ErrorCategory.ASSERTION, message="failed")
        error = error.model_copy(update={"highlight_target": highlight})
        rect = highlight.rect if highlight is not None else None
        await session.hud.mark_failure(rect, error.message)
        await asyncio.sleep(options.failure_hold_ms / 1000)
        shot = None
        full = None
        if options.screenshots is not ScreenshotMode.NONE:
            shot = await self._capture(session, state, planned, "failed", full_page=False)
            full = await self._capture(session, state, planned, "failure_fullpage", full_page=True)
        if not options.continue_on_failure:
            state.abort()
        return result.model_copy(
            update={"error": error, "screenshot": shot, "failure_screenshot": full}
        )

    async def _settle_error(
        self, session: SessionPort, state: RunState, planned: PlannedStep, result: StepResult
    ) -> StepResult:
        message = result.error.message if result.error else "step errored"
        await session.hud.mark_error(message)
        shot = None
        if state.plan.options.screenshots is not ScreenshotMode.NONE:
            shot = await self._capture(session, state, planned, "error", full_page=False)
        state.abort()
        return result.model_copy(update={"screenshot": shot})

    async def _highlight(
        self, session: SessionPort, state: RunState, planned: PlannedStep
    ) -> HighlightTarget | None:
        target = planned.step.target_or_none
        if target is not None:
            rect = await self._quiet_value(session.highlight_rect(target))
            if rect is not None:
                return HighlightTarget(
                    source=HighlightSource.STEP, step_id=planned.step.id, rect=rect
                )
        last = state.last_action
        if last is None or last is planned:
            return None
        last_target = last.step.target_or_none
        if last_target is None:
            return None
        rect = await self._quiet_value(session.highlight_rect(last_target))
        return HighlightTarget(
            source=HighlightSource.PREVIOUS_ACTION, step_id=last.step.id, rect=rect
        )

    async def _capture(
        self,
        session: SessionPort,
        state: RunState,
        planned: PlannedStep,
        suffix: str,
        full_page: bool,
    ) -> str | None:
        relative = f"{ArtifactNames.SCREENSHOTS}/{planned.index:03d}_{suffix}.png"
        path = state.run_dir / relative
        try:
            await session.screenshot(path, full_page)
        except Exception as exc:
            state.warnings.append(f"screenshot for step {planned.step.id} failed: {exc}")
            return None
        state.screenshots.append(relative)
        return relative

    async def _announce(self, session: SessionPort, state: RunState) -> None:
        plan = state.plan
        steps = state.ordered_results()
        outcome, _ = self._evaluator.evaluate(plan, steps, state.run_error)
        verdict = self._policy.decide(plan.kind, plan.mode, outcome)
        headline = self._composer.headline(plan, verdict, steps, state.run_error)
        await session.hud.set_final(verdict, headline)

    async def _close(self, session: SessionPort, state: RunState) -> ClosedSession:
        options = state.plan.options
        try:
            async with asyncio.timeout(self._settings.session_close_timeout_s):
                return await session.close()
        except Exception as exc:
            log.exception("closing session of run %s failed", state.run_id)
            state.warnings.append(f"closing the browser session failed: {exc}")
            return ClosedSession(
                browser=BrowserInfo(
                    name=options.browser,
                    version=None,
                    headless=options.headless,
                    viewport=options.environment.viewport,
                )
            )

    async def _finish(
        self,
        session: SessionPort,
        state: RunState,
        closed: ClosedSession,
        started_at: datetime,
    ) -> RunResult:
        request = FinalizeRequest(
            plan=state.plan,
            run_id=state.run_id,
            run_dir=state.run_dir,
            steps=state.ordered_results(),
            closed=closed,
            observed=session.observations(),
            started_at=started_at,
            run_error=state.run_error,
            warnings=list(state.warnings),
            screenshots=list(state.screenshots),
        )
        return await self._finalizer.finish(request)

    @staticmethod
    def _run_error_message(state: RunState) -> str:
        return state.run_error.message if state.run_error else "run aborted"

    @staticmethod
    async def _quiet(call: Awaitable[None]) -> None:
        try:
            async with asyncio.timeout(HUD_CALL_TIMEOUT_S):
                await call
        except Exception:
            log.debug("ignored failure while updating the HUD", exc_info=True)

    @staticmethod
    async def _quiet_value[T](call: Awaitable[T | None]) -> T | None:
        try:
            async with asyncio.timeout(HUD_CALL_TIMEOUT_S):
                return await call
        except Exception:
            log.debug("ignored failure while resolving a highlight", exc_info=True)
            return None
