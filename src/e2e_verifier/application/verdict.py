from __future__ import annotations

from e2e_verifier.application.compiler import ExecutionPlan
from e2e_verifier.domain.enums import (
    CriterionStatus,
    Outcome,
    RunKind,
    RunMode,
    StepStatus,
    Verdict,
)
from e2e_verifier.domain.result import (
    CriterionEvidence,
    CriterionResult,
    Observations,
    StepError,
    StepResult,
)


class OutcomeEvaluator:
    def evaluate(
        self, plan: ExecutionPlan, steps: list[StepResult], run_error: StepError | None
    ) -> tuple[Outcome, list[CriterionResult]]:
        by_id = {step.id: step for step in steps}
        criteria = [
            self._criterion(criterion.id, criterion.description, criterion.step_ids, by_id)
            for criterion in plan.criteria
        ]
        if run_error is not None or any(step.status is StepStatus.ERROR for step in steps):
            return Outcome.ERROR, criteria
        if any(criterion.status is not CriterionStatus.MET for criterion in criteria):
            return Outcome.CRITERIA_NOT_MET, criteria
        return Outcome.CRITERIA_MET, criteria

    @staticmethod
    def _criterion(
        criterion_id: str,
        description: str,
        step_ids: list[str],
        by_id: dict[str, StepResult],
    ) -> CriterionResult:
        results = [by_id[step_id] for step_id in step_ids if step_id in by_id]
        statuses = {result.status for result in results}
        if StepStatus.FAILED in statuses:
            status = CriterionStatus.NOT_MET
        elif statuses and statuses <= {StepStatus.PASSED}:
            status = CriterionStatus.MET
        else:
            status = CriterionStatus.UNKNOWN
        evidence_step = next(
            (result for result in results if result.status is StepStatus.FAILED),
            results[0] if results else None,
        )
        evidence = None
        if evidence_step is not None and status is not CriterionStatus.UNKNOWN:
            evidence = CriterionEvidence(
                step_id=evidence_step.id,
                video_offset_ms=evidence_step.started_offset_ms,
                screenshot=evidence_step.failure_screenshot or evidence_step.screenshot,
                trace_group=evidence_step.trace_group,
            )
        return CriterionResult(
            id=criterion_id,
            description=description,
            status=status,
            step_ids=list(step_ids),
            evidence=evidence,
        )


class VerdictPolicy:
    def decide(self, kind: RunKind, mode: RunMode, outcome: Outcome) -> Verdict:
        if outcome is Outcome.ERROR:
            return Verdict.INCONCLUSIVE
        met = outcome is Outcome.CRITERIA_MET
        if kind is RunKind.SCENARIO:
            return Verdict.PASSED if met else Verdict.FAILED
        if mode is RunMode.REPRODUCE:
            return Verdict.NOT_REPRODUCED if met else Verdict.REPRODUCED
        return Verdict.FIXED if met else Verdict.STILL_BROKEN


class SummaryComposer:
    def compose(
        self,
        plan: ExecutionPlan,
        verdict: Verdict,
        steps: list[StepResult],
        observations: Observations,
        run_error: StepError | None,
    ) -> str:
        lead = self.headline(plan, verdict, steps, run_error)
        counts = (
            f"{observations.console_errors} console errors, "
            f"{observations.page_errors} page errors, "
            f"{observations.failed_requests} failed requests."
        )
        after = self._requests_after_last_action(plan, steps, observations)
        return " ".join(part for part in (lead, after, counts) if part)

    @staticmethod
    def headline(
        plan: ExecutionPlan,
        verdict: Verdict,
        steps: list[StepResult],
        run_error: StepError | None,
    ) -> str:
        failed = next((step for step in steps if step.status is StepStatus.FAILED), None)
        errored = next((step for step in steps if step.status is StepStatus.ERROR), None)
        if verdict is Verdict.INCONCLUSIVE:
            source = run_error or (errored.error if errored else None)
            where = f" at step {errored.id} ({errored.title})" if errored else ""
            detail = f": {source.message}" if source else ""
            return f"Run inconclusive{where}{detail}"
        if failed is not None:
            detail = " ".join(failed.error.message.split()) if failed.error else "assertion failed"
            prefix = {
                Verdict.REPRODUCED: "Bug reproduced",
                Verdict.STILL_BROKEN: "Bug still present",
                Verdict.FAILED: "Scenario failed",
            }.get(verdict, "Failed")
            return f"{prefix}: step {failed.id} ({failed.title}) failed: {detail}"
        prefix = {
            Verdict.FIXED: "All acceptance criteria met; bug not observed",
            Verdict.NOT_REPRODUCED: "Bug not reproduced; all acceptance criteria met",
            Verdict.PASSED: "Scenario passed",
        }.get(verdict, "Passed")
        return f"{prefix} for {plan.ticket_id}."

    @staticmethod
    def _requests_after_last_action(
        plan: ExecutionPlan, steps: list[StepResult], observations: Observations
    ) -> str:
        action_ids = [planned.step.id for planned in plan.steps if not planned.step.is_assertion]
        executed = [
            step for step in steps if step.id in action_ids and step.status is StepStatus.PASSED
        ]
        if not executed:
            return ""
        last = executed[-1]
        count = observations.requests_after_step.get(last.id)
        if count is None:
            return ""
        return f"Requests after last action ({last.title}): {count}."
