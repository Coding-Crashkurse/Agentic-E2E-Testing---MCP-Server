from __future__ import annotations

from typing import Any, cast

from pydantic import Field

from e2e_verifier.application.compiler import ExecutionPlan, PlanCompiler
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.ports import SessionFactoryPort, SessionPort
from e2e_verifier.domain.aria import ARIA_ROLES, AriaRole
from e2e_verifier.domain.common import StrictModel
from e2e_verifier.domain.enums import StepStatus
from e2e_verifier.domain.errors import VerifierError
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import DiscoveryResult, ElementCandidate, ProbeResult, Rect
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import GotoStep, RoleTarget, Step, Target, TextTarget
from e2e_verifier.domain.ticket import Scenario

PROBE_TIMEOUT_MS = 15_000
HTTP_ERROR_STATUS = 400
ARIA_SNAPSHOT_MAX_CHARS = 20_000
DISCOVERY_OPEN_STEP_ID = "__discovery_open__"
FORM_TAGS = frozenset({"input", "select", "textarea"})


class RawCandidate(StrictModel):
    tag: str
    role: str | None = None
    name: str | None = None
    label: str | None = None
    placeholder: str | None = None
    test_id: str | None = None
    element_id: str | None = None
    css: str
    visible: bool
    disabled: bool = False
    rect: Rect = Field(default_factory=lambda: Rect(x=0, y=0, width=0, height=0))


class TargetSuggester:
    def suggest_from(self, item: dict[str, Any]) -> Target:
        return self.suggest(RawCandidate.model_validate(item))

    def suggest(self, raw: RawCandidate) -> Target:
        if raw.test_id:
            return Target(test_id=raw.test_id)
        if raw.role in ARIA_ROLES and raw.name:
            role = cast("AriaRole", raw.role)
            return Target(role=RoleTarget(role=role, name=raw.name, exact=True))
        if raw.tag in FORM_TAGS:
            if raw.label:
                return Target(label=raw.label)
            if raw.placeholder:
                return Target(placeholder=raw.placeholder)
        if raw.name and raw.tag not in FORM_TAGS:
            return Target(text=TextTarget(text=raw.name, exact=True))
        return Target(css=raw.css)


class TargetProbe:
    def __init__(
        self,
        sessions: SessionFactoryPort,
        compiler: PlanCompiler,
        allowlist: HostAllowlist,
        settings: Settings,
    ) -> None:
        self._sessions = sessions
        self._compiler = compiler
        self._allowlist = allowlist
        self._settings = settings

    async def probe(self, url: str) -> ProbeResult:
        self._allowlist.ensure(url)
        plan = self._plan(url)
        session = self._sessions.create(plan, None, light=True)
        try:
            await session.open()
            return await self._navigate(session, url)
        finally:
            await session.close()

    async def _navigate(self, session: SessionPort, url: str) -> ProbeResult:
        try:
            navigation = await session.navigate_probe(url, PROBE_TIMEOUT_MS)
        except Exception as exc:
            observed = session.observations()
            return ProbeResult(
                url=url,
                final_url=None,
                reachable=False,
                status=None,
                title=None,
                load_time_ms=None,
                console_errors=[entry.text for entry in observed.console if entry.level == "error"],
                page_errors=[
                    entry.text for entry in observed.console if entry.level == "pageerror"
                ],
                error=f"{type(exc).__name__}: {exc}",
            )
        observed = session.observations()
        return ProbeResult(
            url=url,
            final_url=navigation.final_url,
            reachable=navigation.status is not None and navigation.status < HTTP_ERROR_STATUS,
            status=navigation.status,
            title=navigation.title,
            load_time_ms=navigation.load_time_ms,
            console_errors=[entry.text for entry in observed.console if entry.level == "error"],
            page_errors=[entry.text for entry in observed.console if entry.level == "pageerror"],
            error=None,
        )

    def _plan(self, url: str) -> ExecutionPlan:
        scenario = Scenario(
            id="probe", title="probe", url=url, steps=[GotoStep(id="open", url=url)]
        )
        return self._compiler.compile(scenario, RunOptions())


class ElementDiscovery:
    def __init__(
        self,
        sessions: SessionFactoryPort,
        compiler: PlanCompiler,
        allowlist: HostAllowlist,
        settings: Settings,
    ) -> None:
        self._sessions = sessions
        self._compiler = compiler
        self._allowlist = allowlist
        self._settings = settings
        self._suggester = TargetSuggester()

    async def discover(
        self,
        url: str,
        query: str | None,
        steps_before: list[Step] | None,
        max_results: int,
    ) -> DiscoveryResult:
        self._allowlist.ensure(url)
        plan = self._plan(url, steps_before or [])
        session = self._sessions.create(plan, None, light=True)
        try:
            await session.open()
            await self._prepare(session, plan)
            raw_candidates = await session.discover(query, max_results)
            snapshot = await session.aria_snapshot()
            final_url = session.current_url()
        finally:
            await session.close()
        truncated = len(snapshot) > ARIA_SNAPSHOT_MAX_CHARS
        return DiscoveryResult(
            url=url,
            final_url=final_url,
            query=query,
            candidates=[self._candidate(item) for item in raw_candidates],
            aria_snapshot=snapshot[:ARIA_SNAPSHOT_MAX_CHARS],
            aria_snapshot_truncated=truncated,
        )

    async def _prepare(self, session: SessionPort, plan: ExecutionPlan) -> None:
        for planned in plan.steps:
            outcome = await session.execute(planned, 0)
            if outcome.status is not StepStatus.PASSED:
                message = outcome.error.message if outcome.error else outcome.status
                raise VerifierError(f"steps_before failed at step {planned.step.id}: {message}")

    def _plan(self, url: str, steps_before: list[Step]) -> ExecutionPlan:
        steps: list[Step] = [GotoStep(id=DISCOVERY_OPEN_STEP_ID, url=url), *steps_before]
        scenario = Scenario(id="discovery", title="discovery", url=url, steps=steps)
        return self._compiler.compile(scenario, RunOptions())

    def _candidate(self, item: dict[str, Any]) -> ElementCandidate:
        raw = RawCandidate.model_validate(item)
        return ElementCandidate(
            tag=raw.tag,
            role=raw.role,
            name=raw.name,
            test_id=raw.test_id,
            element_id=raw.element_id,
            css=raw.css,
            visible=raw.visible,
            disabled=raw.disabled,
            rect=raw.rect,
            suggested_target=self._suggester.suggest(raw),
        )
