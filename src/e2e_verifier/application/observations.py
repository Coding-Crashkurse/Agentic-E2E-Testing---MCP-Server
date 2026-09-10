from __future__ import annotations

from e2e_verifier.application.compiler import ExecutionPlan
from e2e_verifier.application.ports import SessionObservations
from e2e_verifier.domain.enums import StepStatus
from e2e_verifier.domain.result import NetworkEntry, Observations, StepResult

PAGE_ERROR_LEVEL = "pageerror"
REQUEST_PHASE = "request"
FAILED_PHASE = "failed"


class ObservationSummarizer:
    def summarize(
        self, plan: ExecutionPlan, steps: list[StepResult], observed: SessionObservations
    ) -> Observations:
        console_errors = sum(1 for entry in observed.console if entry.level == "error")
        page_errors = sum(1 for entry in observed.console if entry.level == PAGE_ERROR_LEVEL)
        requests = [entry for entry in observed.network if entry.phase == REQUEST_PHASE]
        failed = sum(1 for entry in observed.network if entry.phase == FAILED_PHASE)
        return Observations(
            console_errors=console_errors,
            page_errors=page_errors,
            failed_requests=failed,
            requests_total=len(requests),
            requests_after_step=self._requests_after_actions(plan, steps, requests),
            dialogs=len(observed.dialogs),
            downloads=len(observed.downloads),
            truncated=observed.truncated,
        )

    @staticmethod
    def _requests_after_actions(
        plan: ExecutionPlan,
        steps: list[StepResult],
        requests: list[NetworkEntry],
    ) -> dict[str, int]:
        assertion_ids = {planned.step.id for planned in plan.steps if planned.step.is_assertion}
        actions = [
            step
            for step in steps
            if step.id not in assertion_ids
            and step.status in {StepStatus.PASSED, StepStatus.FAILED}
            and step.started_offset_ms is not None
        ]
        offsets = [entry.offset_ms for entry in requests]
        counts: dict[str, int] = {}
        for position, step in enumerate(actions):
            start = step.started_offset_ms or 0
            following = actions[position + 1 : position + 2]
            end = following[0].started_offset_ms if following else None
            counts[step.id] = sum(
                1 for offset in offsets if offset >= start and (end is None or offset < end)
            )
        return counts
