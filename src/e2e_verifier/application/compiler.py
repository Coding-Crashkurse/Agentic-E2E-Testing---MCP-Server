from __future__ import annotations

from pydantic import Field

from e2e_verifier.application.urls import UrlRewriter
from e2e_verifier.domain.common import FrozenModel
from e2e_verifier.domain.enums import RunKind, RunMode, StepPhase
from e2e_verifier.domain.masking import SecretMasker
from e2e_verifier.domain.options import EffectiveOptions, RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import GotoStep, Step, StepBase
from e2e_verifier.domain.ticket import AcceptanceCriterion, BugTicket, Environment, Scenario

IMPLICIT_GOTO_ID = "__open__"


class PlannedStep(FrozenModel):
    index: int
    step: Step
    phase: StepPhase
    title: str
    trace_group: str

    @property
    def base(self) -> StepBase:
        return self.step


class ExecutionPlan(FrozenModel):
    kind: RunKind
    ticket_id: str
    title: str
    description: str | None
    expected: str | None
    actual: str | None
    mode: RunMode
    target_url: str
    original_url: str
    base_url_override: str | None
    steps: list[PlannedStep]
    criteria: list[AcceptanceCriterion]
    options: EffectiveOptions
    source: BugTicket | Scenario
    secrets: list[str] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def criterion_step_ids(self) -> set[str]:
        return {step_id for criterion in self.criteria for step_id in criterion.step_ids}

    def rewriter(self) -> UrlRewriter:
        return UrlRewriter(self.original_url, self.base_url_override)


class OptionsResolver:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def resolve(self, options: RunOptions, environment: Environment) -> EffectiveOptions:
        settings = self._settings
        run_timeout = options.run_timeout_s or settings.default_run_timeout_s
        return EffectiveOptions(
            mode=options.mode,
            browser=options.browser or environment.browser or settings.browser,
            headless=settings.headless if options.headless is None else options.headless,
            step_timeout_ms=options.step_timeout_ms or settings.default_step_timeout_ms,
            run_timeout_s=min(run_timeout, settings.max_run_timeout_s),
            continue_on_failure=options.continue_on_failure,
            failure_hold_ms=options.failure_hold_ms,
            post_roll_ms=options.post_roll_ms,
            slow_mo_ms=options.slow_mo_ms,
            record_har=options.record_har,
            screenshots=options.screenshots,
            hud_enabled=options.hud.enabled,
            hud_position=options.hud.position,
            hud_language=options.hud.language or settings.hud_language,
            hud_show_timer=options.hud.show_timer,
            hud_show_ticket_id=options.hud.show_ticket_id,
            label=options.label,
            environment=environment,
        )


class PlanCompiler:
    def __init__(self, settings: Settings, masker: SecretMasker | None = None) -> None:
        self._resolver = OptionsResolver(settings)
        self._masker = masker or SecretMasker()

    def compile(self, source: BugTicket | Scenario, options: RunOptions | None) -> ExecutionPlan:
        effective = self._resolver.resolve(options or RunOptions(), source.environment)
        override = str(options.base_url_override) if options and options.base_url_override else None
        rewriter = UrlRewriter(str(source.url), override)
        steps = self._plan_steps(source, rewriter)
        kind = RunKind.TICKET if isinstance(source, BugTicket) else RunKind.SCENARIO
        return ExecutionPlan(
            kind=kind,
            ticket_id=source.id,
            title=source.title,
            description=source.description,
            expected=source.expected if isinstance(source, BugTicket) else None,
            actual=source.actual if isinstance(source, BugTicket) else None,
            mode=effective.mode if kind is RunKind.TICKET else RunMode.VERIFY,
            target_url=rewriter.target_url,
            original_url=rewriter.original_url,
            base_url_override=override,
            steps=steps,
            criteria=self._criteria(source),
            options=effective,
            source=self._masker.mask_source(source),
            secrets=self._masker.secret_values(source),
        )

    def _plan_steps(self, source: BugTicket | Scenario, rewriter: UrlRewriter) -> list[PlannedStep]:
        preconditions: list[StepBase] = list(source.preconditions)
        first = source.steps[0]
        if not preconditions and not isinstance(first, GotoStep):
            preconditions.append(GotoStep(id=IMPLICIT_GOTO_ID, url=rewriter.target_url))
        total = len(preconditions) + len(source.steps)
        planned: list[PlannedStep] = []
        for step in preconditions:
            planned.append(self._planned(step, len(planned) + 1, total, StepPhase.PRECONDITIONS))
        for step in source.steps:
            planned.append(self._planned(step, len(planned) + 1, total, StepPhase.STEPS))
        return planned

    @staticmethod
    def _planned(step: StepBase, index: int, total: int, phase: StepPhase) -> PlannedStep:
        title = step.display_title()
        label = "Setup" if phase is StepPhase.PRECONDITIONS else "Step"
        return PlannedStep(
            index=index,
            step=step,
            phase=phase,
            title=title,
            trace_group=f"{label} {index}/{total}: {title}",
        )

    @staticmethod
    def _criteria(source: BugTicket | Scenario) -> list[AcceptanceCriterion]:
        if isinstance(source, BugTicket):
            return list(source.acceptance_criteria)
        return [
            AcceptanceCriterion(id=step.id, description=step.display_title(), step_ids=[step.id])
            for step in source.steps
            if step.is_assertion
        ]
