from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from e2e_verifier.application.clock import Clock
from e2e_verifier.application.compiler import ExecutionPlan, PlanCompiler, PlannedStep
from e2e_verifier.application.exploration import TargetSuggester
from e2e_verifier.application.finalize import FinalizeRequest, RunFinalizer
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.ports import ClosedSession, SessionFactoryPort, SessionPort
from e2e_verifier.application.registry import RunRegistry
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.application.verdict import OutcomeEvaluator, SummaryComposer, VerdictPolicy
from e2e_verifier.domain.enums import (
    AnnotationTone,
    ErrorCategory,
    HighlightSource,
    StepPhase,
    StepStatus,
    Verdict,
)
from e2e_verifier.domain.errors import SessionNotFoundError, TooManySessionsError
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import (
    ActResult,
    AnnotationResult,
    BrowserInfo,
    DiscoveryResult,
    ElementCandidate,
    HighlightTarget,
    Rect,
    RunResult,
    SessionInfo,
    StepError,
    StepResult,
)
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import GotoStep, StepBase, Target
from e2e_verifier.domain.ticket import Scenario

log = logging.getLogger(__name__)

OPEN_STEP_ID = "open"
DEFAULT_LABEL = "Interactive session"
MAX_HOLD_MS = 10_000
MAX_LISTED_ERRORS = 5
ARIA_SNAPSHOT_MAX_CHARS = 20_000


class InteractiveSession:
    def __init__(
        self,
        session_id: str,
        run_dir: Path,
        plan: ExecutionPlan,
        options: RunOptions,
        session: SessionPort,
        compiler: PlanCompiler,
        finalizer: RunFinalizer,
        clock: Clock,
        settings: Settings,
    ) -> None:
        self.session_id = session_id
        self.run_dir = run_dir
        self._plan = plan
        self._options = options
        self._session = session
        self._compiler = compiler
        self._finalizer = finalizer
        self._clock = clock
        self._settings = settings
        self.lock = asyncio.Lock()
        self.opened_at: datetime = clock.now()
        self.steps: list[StepResult] = []
        self.executed: list[StepBase] = []
        self.annotations: list[AnnotationResult] = []
        self.screenshots: list[str] = []
        self.warnings: list[str] = []
        self.title = ""
        self._last_activity_ms = clock.monotonic_ms()
        self._last_action: PlannedStep | None = None
        self._window_start_ms = 0
        self._captures = 0
        self._console_seen = 0
        self._requests_seen = 0
        self._used_ids: set[str] = set()
        self._closed = False
        self._suggester = TargetSuggester()

    @property
    def label(self) -> str:
        return self._options.label or DEFAULT_LABEL

    @property
    def idle_ms(self) -> int:
        return self._clock.monotonic_ms() - self._last_activity_ms

    @property
    def closed(self) -> bool:
        return self._closed

    def info(self) -> SessionInfo:
        failed = sum(1 for step in self.steps if step.status is not StepStatus.PASSED)
        return SessionInfo(
            session_id=self.session_id,
            label=self.label,
            url=self._session.current_url(),
            title=self.title,
            steps_executed=len(self.steps),
            failed_steps=failed,
            annotations=len(self.annotations),
            opened_at=self.opened_at,
            idle_seconds=self.idle_ms // 1000,
            artifacts_dir=str(self.run_dir),
        )

    async def open(self) -> ActResult:
        await self._session.open()
        return await self.act(GotoStep(id=OPEN_STEP_ID, url=self._plan.target_url))

    async def act(self, step: StepBase) -> ActResult:
        self._touch()
        step = self._with_unique_id(step)
        index = len(self.steps) + 1
        title = step.display_title()
        planned = PlannedStep(
            index=index,
            step=step,
            phase=StepPhase.STEPS,
            title=title,
            trace_group=f"Step {index}: {title}",
        )
        await self._session.hud.clear_annotation()
        await self._session.hud.set_step(index, 0, title, StepPhase.STEPS)
        started = self._session.offset_ms()
        async with await self._session.trace_group(planned.trace_group):
            outcome = await self._session.execute(planned, self._window_start_ms)
        ended = self._session.offset_ms()
        if not step.is_assertion:
            self._last_action = planned
            self._window_start_ms = started
        error = outcome.error
        if outcome.status is StepStatus.PASSED:
            await self._session.hud.mark_success()
        elif outcome.status is StepStatus.FAILED:
            highlight = await self._highlight(planned)
            message = error.message if error else "step failed"
            error = (
                error or StepError(category=ErrorCategory.ASSERTION, message=message)
            ).model_copy(update={"highlight_target": highlight})
            await self._session.hud.mark_failure(highlight.rect if highlight else None, message)
        else:
            await self._session.hud.mark_error(error.message if error else "step errored")
        screenshot = await self._capture(f"{index:03d}_{outcome.status}", full_page=False)
        result = StepResult(
            index=index,
            id=step.id,
            phase=StepPhase.STEPS,
            action=planned.step.action,
            title=title,
            status=outcome.status,
            started_offset_ms=started,
            ended_offset_ms=ended,
            error=error,
            screenshot=screenshot,
            trace_group=planned.trace_group,
        )
        self.steps.append(result)
        self.executed.append(step)
        self.title = await self._session.page_title()
        return self._act_result(result, screenshot)

    async def annotate(
        self, message: str, target: Target | None, tone: AnnotationTone, hold_ms: int
    ) -> AnnotationResult:
        self._touch()
        rect = None
        if target is not None:
            rect = await self._quiet_rect(target)
        await self._session.hud.annotate(rect, message, tone)
        await asyncio.sleep(min(max(hold_ms, 0), MAX_HOLD_MS) / 1000)
        index = len(self.annotations) + 1
        screenshot = await self._capture(f"note{index:03d}_{tone}", full_page=False)
        result = AnnotationResult(
            session_id=self.session_id,
            index=index,
            message=message,
            tone=tone,
            rect=rect,
            screenshot=screenshot,
        )
        self.annotations.append(result)
        return result

    async def screenshot(self, full_page: bool) -> str | None:
        self._touch()
        return await self._capture(f"shot{self._captures + 1:03d}", full_page=full_page)

    async def inline_screenshot(self) -> bytes:
        return await self._session.screenshot_bytes(
            full_page=False, jpeg_quality=self._settings.inline_screenshot_quality
        )

    async def inspect(self, query: str | None, max_results: int) -> DiscoveryResult:
        self._touch()
        raw = await self._session.discover(query, max_results)
        snapshot = await self._session.aria_snapshot()
        candidates = [
            ElementCandidate(
                tag=str(item.get("tag", "")),
                role=item.get("role"),
                name=item.get("name"),
                test_id=item.get("test_id"),
                element_id=item.get("element_id"),
                css=str(item.get("css", "")),
                visible=bool(item.get("visible", False)),
                disabled=bool(item.get("disabled", False)),
                rect=Rect.model_validate(
                    item.get("rect") or {"x": 0, "y": 0, "width": 0, "height": 0}
                ),
                suggested_target=self._suggester.suggest_from(item),
            )
            for item in raw
        ]
        return DiscoveryResult(
            url=self._plan.target_url,
            final_url=self._session.current_url(),
            query=query,
            candidates=candidates,
            aria_snapshot=snapshot[:ARIA_SNAPSHOT_MAX_CHARS],
            aria_snapshot_truncated=len(snapshot) > ARIA_SNAPSHOT_MAX_CHARS,
        )

    async def close(self, verdict: Verdict | None, summary: str | None) -> RunResult:
        self._closed = True
        final_plan = self._final_plan()
        derived = self._derive_verdict(final_plan)
        headline = summary or SummaryComposer().headline(final_plan, derived, self.steps, None)
        await self._quiet(self._session.hud.clear_annotation())
        await self._quiet(self._session.hud.set_final(verdict or derived, headline))
        await asyncio.sleep(self._options.post_roll_ms / 1000)
        closed = await self._close_browser()
        request = FinalizeRequest(
            plan=final_plan,
            run_id=self.session_id,
            run_dir=self.run_dir,
            steps=list(self.steps),
            closed=closed,
            observed=self._session.observations(),
            started_at=self.opened_at,
            warnings=list(self.warnings),
            screenshots=list(self.screenshots),
            verdict_override=verdict,
            summary_override=summary,
        )
        return await self._finalizer.finish(request)

    async def abort(self) -> None:
        self._closed = True
        await self._quiet(self._close_browser_raw())

    def _final_plan(self) -> ExecutionPlan:
        scenario = Scenario(
            id=self.session_id,
            title=self.label,
            url=self._plan.original_url,
            steps=list(self.executed) or [GotoStep(id=OPEN_STEP_ID, url=self._plan.target_url)],
        )
        return self._compiler.compile(scenario, self._options)

    def _derive_verdict(self, plan: ExecutionPlan) -> Verdict:
        outcome, _ = OutcomeEvaluator().evaluate(plan, self.steps, None)
        return VerdictPolicy().decide(plan.kind, plan.mode, outcome)

    def _act_result(self, result: StepResult, screenshot: str | None) -> ActResult:
        observed = self._session.observations()
        console = [entry for entry in observed.console if entry.level in {"error", "pageerror"}]
        new_console = console[self._console_seen :]
        self._console_seen = len(console)
        requests = [entry for entry in observed.network if entry.phase == "request"]
        new_requests = len(requests) - self._requests_seen
        self._requests_seen = len(requests)
        hint = None
        if result.status is StepStatus.FAILED:
            hint = (
                "The step failed; the HUD shows a red frame in the video. Use session_inspect to "
                "look at the page, session_annotate to mark findings, or continue with more steps."
            )
        elif result.status is StepStatus.ERROR:
            hint = "The step errored (see error.category); fix the target or URL and retry."
        return ActResult(
            session_id=self.session_id,
            step=result,
            url=self._session.current_url(),
            title=self.title,
            screenshot=screenshot,
            new_console_errors=[
                entry.text.splitlines()[0] for entry in new_console if entry.level == "error"
            ][:MAX_LISTED_ERRORS],
            new_page_errors=[
                entry.text.splitlines()[0] for entry in new_console if entry.level == "pageerror"
            ][:MAX_LISTED_ERRORS],
            new_requests=new_requests,
            hint=hint,
        )

    async def _highlight(self, planned: PlannedStep) -> HighlightTarget | None:
        target = planned.step.target_or_none
        if target is not None:
            rect = await self._quiet_rect(target)
            if rect is not None:
                return HighlightTarget(
                    source=HighlightSource.STEP, step_id=planned.step.id, rect=rect
                )
        last = self._last_action
        if last is None or last is planned or last.step.target_or_none is None:
            return None
        rect = await self._quiet_rect(last.step.target_or_none)
        return HighlightTarget(
            source=HighlightSource.PREVIOUS_ACTION, step_id=last.step.id, rect=rect
        )

    async def _capture(self, name: str, full_page: bool) -> str | None:
        relative = f"{ArtifactNames.SCREENSHOTS}/{name}.png"
        try:
            await self._session.screenshot(self.run_dir / relative, full_page)
        except Exception as exc:
            self.warnings.append(f"screenshot {name} failed: {exc}")
            return None
        self._captures += 1
        self.screenshots.append(relative)
        return relative

    async def _close_browser(self) -> ClosedSession:
        try:
            async with asyncio.timeout(self._settings.session_close_timeout_s):
                return await self._session.close()
        except Exception as exc:
            log.exception("closing interactive session %s failed", self.session_id)
            self.warnings.append(f"closing the browser session failed: {exc}")
            options = self._plan.options
            return ClosedSession(
                browser=BrowserInfo(
                    name=options.browser,
                    version=None,
                    headless=options.headless,
                    viewport=options.environment.viewport,
                )
            )

    async def _close_browser_raw(self) -> None:
        async with asyncio.timeout(self._settings.session_close_timeout_s):
            await self._session.close()

    def _with_unique_id(self, step: StepBase) -> StepBase:
        candidate = step.id
        suffix = 2
        while candidate in self._used_ids:
            candidate = f"{step.id}_{suffix}"
            suffix += 1
        self._used_ids.add(candidate)
        if candidate == step.id:
            return step
        return step.model_copy(update={"id": candidate})

    def _touch(self) -> None:
        self._last_activity_ms = self._clock.monotonic_ms()

    async def _quiet_rect(self, target: Target) -> Rect | None:
        try:
            return await self._session.highlight_rect(target)
        except Exception:
            log.debug("highlight lookup failed", exc_info=True)
            return None

    @staticmethod
    async def _quiet(call: object) -> None:
        try:
            if asyncio.iscoroutine(call):
                await call
        except Exception:
            log.debug("ignored failure in interactive session cleanup", exc_info=True)


class SessionManager:
    def __init__(
        self,
        sessions: SessionFactoryPort,
        compiler: PlanCompiler,
        store: ArtifactStore,
        registry: RunRegistry,
        finalizer: RunFinalizer,
        clock: Clock,
        settings: Settings,
        allowlist: HostAllowlist,
    ) -> None:
        self._sessions = sessions
        self._compiler = compiler
        self._store = store
        self._registry = registry
        self._finalizer = finalizer
        self._clock = clock
        self._settings = settings
        self._allowlist = allowlist
        self._active: dict[str, InteractiveSession] = {}

    async def open(
        self, url: str, options: RunOptions | None
    ) -> tuple[InteractiveSession, ActResult]:
        self._allowlist.ensure(url)
        await self.reap_idle()
        if len(self._active) >= self._settings.max_sessions:
            raise TooManySessionsError(self._settings.max_sessions)
        options = options or RunOptions()
        location = self._store.create_run()
        scenario = Scenario(
            id=location.run_id,
            title=options.label or DEFAULT_LABEL,
            url=url,
            steps=[GotoStep(id=OPEN_STEP_ID, url=url)],
        )
        plan = self._compiler.compile(scenario, options)
        browser_session = self._sessions.create(plan, location.path, light=False)
        interactive = InteractiveSession(
            session_id=location.run_id,
            run_dir=location.path,
            plan=plan,
            options=options,
            session=browser_session,
            compiler=self._compiler,
            finalizer=self._finalizer,
            clock=self._clock,
            settings=self._settings,
        )
        self._registry.mark_running(location.run_id)
        try:
            first = await interactive.open()
        except Exception:
            await interactive.abort()
            self._registry.mark_finished(location.run_id)
            raise
        self._active[location.run_id] = interactive
        return interactive, first

    def get(self, session_id: str) -> InteractiveSession:
        session = self._active.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def list_open(self) -> list[SessionInfo]:
        return [session.info() for session in self._active.values()]

    async def close(
        self, session_id: str, verdict: Verdict | None, summary: str | None
    ) -> RunResult:
        session = self.get(session_id)
        async with session.lock:
            self._active.pop(session_id, None)
            try:
                return await session.close(verdict, summary)
            finally:
                self._registry.mark_finished(session_id)

    async def close_all(self) -> None:
        for session_id in list(self._active):
            try:
                await self.close(session_id, None, "closed on server shutdown")
            except Exception:
                log.exception("closing interactive session %s failed", session_id)

    async def reap_idle(self) -> list[str]:
        limit_ms = self._settings.session_idle_timeout_s * 1000
        reaped: list[str] = []
        for session_id, session in list(self._active.items()):
            if session.idle_ms < limit_ms or session.lock.locked():
                continue
            try:
                await self.close(session_id, None, "closed automatically after the idle timeout")
            except Exception:
                log.exception("reaping interactive session %s failed", session_id)
            reaped.append(session_id)
        return reaped
