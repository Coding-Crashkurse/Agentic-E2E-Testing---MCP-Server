from __future__ import annotations

from e2e_verifier.application.fixtures import FixturePaths
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.urls import UrlRewriter
from e2e_verifier.domain.errors import FixturePathError
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import ValidationIssue, ValidationReport
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import FillStep, GotoStep, SleepStep, StepBase, UploadFileStep
from e2e_verifier.domain.ticket import BugTicket, Scenario

BRITTLE_STRATEGIES = frozenset({"css", "xpath"})


class TicketValidator:
    def __init__(self, settings: Settings, allowlist: HostAllowlist) -> None:
        self._settings = settings
        self._allowlist = allowlist
        self._fixtures = FixturePaths(settings.fixture_dir)

    def validate(
        self, source: BugTicket | Scenario, options: RunOptions | None = None
    ) -> ValidationReport:
        options = options or RunOptions()
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        override = str(options.base_url_override) if options.base_url_override else None
        rewriter = UrlRewriter(str(source.url), override)
        self._check_hosts(source, rewriter, errors)
        self._check_options(options, errors)
        self._check_environment(source, errors)
        for step in source.all_steps():
            self._check_step(step, errors, warnings)
        self._check_coverage(source, warnings)
        return ValidationReport(ok=not errors, errors=errors, warnings=warnings)

    def _check_hosts(
        self, source: BugTicket | Scenario, rewriter: UrlRewriter, errors: list[ValidationIssue]
    ) -> None:
        if not self._allowlist.allows(rewriter.target_url):
            errors.append(
                ValidationIssue(
                    code="host_not_allowed",
                    message=f"Host of {rewriter.target_url} is not on the allowlist "
                    f"{self._allowlist.patterns}",
                )
            )
        for step in source.all_steps():
            if isinstance(step, GotoStep):
                resolved = rewriter.resolve(step.url)
                if not self._allowlist.allows(resolved):
                    errors.append(
                        ValidationIssue(
                            code="host_not_allowed",
                            message=f"goto target {resolved} is not on the allowlist",
                            step_id=step.id,
                        )
                    )

    def _check_options(self, options: RunOptions, errors: list[ValidationIssue]) -> None:
        if (
            options.run_timeout_s is not None
            and options.run_timeout_s > self._settings.max_run_timeout_s
        ):
            errors.append(
                ValidationIssue(
                    code="run_timeout_too_large",
                    message=f"run_timeout_s exceeds E2E_MAX_RUN_TIMEOUT_S "
                    f"({self._settings.max_run_timeout_s})",
                )
            )

    def _check_environment(
        self, source: BugTicket | Scenario, errors: list[ValidationIssue]
    ) -> None:
        path = source.environment.storage_state_path
        if path is None:
            return
        try:
            self._fixtures.resolve(path)
        except FixturePathError as exc:
            errors.append(ValidationIssue(code="storage_state_path", message=str(exc)))

    def _check_step(
        self, step: StepBase, errors: list[ValidationIssue], warnings: list[ValidationIssue]
    ) -> None:
        if isinstance(step, UploadFileStep):
            try:
                self._fixtures.resolve(step.path)
            except FixturePathError as exc:
                errors.append(
                    ValidationIssue(code="upload_path", message=str(exc), step_id=step.id)
                )
        if isinstance(step, SleepStep):
            warnings.append(
                ValidationIssue(
                    code="sleep_step",
                    message="sleep makes runs slower and less deterministic; prefer wait_for",
                    step_id=step.id,
                )
            )
        if isinstance(step, FillStep) and step.secret:
            warnings.append(
                ValidationIssue(
                    code="secret_in_trace",
                    message="secret values are masked in reports but remain in trace.zip",
                    step_id=step.id,
                )
            )
        target = step.target_or_none
        if target is not None and target.strategy in BRITTLE_STRATEGIES:
            warnings.append(
                ValidationIssue(
                    code="brittle_selector",
                    message=f"{target.strategy} selectors break easily; prefer role, label "
                    "or test_id",
                    step_id=step.id,
                )
            )

    @staticmethod
    def _check_coverage(source: BugTicket | Scenario, warnings: list[ValidationIssue]) -> None:
        assertions = [step for step in source.steps if step.is_assertion]
        if not assertions:
            warnings.append(
                ValidationIssue(
                    code="no_assertions",
                    message="no assertion steps; the run can only fail on errors",
                )
            )
            return
        if not isinstance(source, BugTicket):
            return
        referenced = {
            step_id for criterion in source.acceptance_criteria for step_id in criterion.step_ids
        }
        warnings.extend(
            ValidationIssue(
                code="unreferenced_assertion",
                message="assertion is not referenced by any acceptance criterion",
                step_id=step.id,
            )
            for step in assertions
            if step.id not in referenced
        )
