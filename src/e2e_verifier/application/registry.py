from __future__ import annotations

from e2e_verifier.application.store import ArtifactStore
from e2e_verifier.domain.enums import Outcome, StepStatus
from e2e_verifier.domain.errors import RunInProgressError, RunNotFoundError
from e2e_verifier.domain.result import RunResult, RunSummary


class RunRegistry:
    def __init__(self, store: ArtifactStore) -> None:
        self._store = store
        self._running: set[str] = set()

    def mark_running(self, run_id: str) -> None:
        self._running.add(run_id)

    def mark_finished(self, run_id: str) -> None:
        self._running.discard(run_id)

    def is_running(self, run_id: str) -> bool:
        return run_id in self._running

    @property
    def running_ids(self) -> set[str]:
        return set(self._running)

    def get(self, run_id: str) -> RunResult:
        if self.is_running(run_id):
            raise RunInProgressError(run_id)
        return self._store.read_result(run_id)

    def list(
        self, limit: int, ticket_id: str | None = None, outcome: Outcome | None = None
    ) -> list[RunSummary]:
        summaries: list[RunSummary] = []
        for run_id in self._store.list_run_ids():
            if len(summaries) >= limit:
                break
            if self.is_running(run_id):
                continue
            try:
                result = self._store.read_result(run_id)
            except (RunNotFoundError, ValueError):
                continue
            if ticket_id is not None and result.ticket_id != ticket_id:
                continue
            if outcome is not None and result.outcome is not outcome:
                continue
            summaries.append(self.summarize(result))
        return summaries

    def count(self) -> int:
        return len(self._store.list_run_ids())

    @staticmethod
    def summarize(result: RunResult) -> RunSummary:
        failed = next(
            (step for step in result.steps if step.status in {StepStatus.FAILED, StepStatus.ERROR}),
            None,
        )
        return RunSummary(
            run_id=result.run_id,
            kind=result.kind,
            ticket_id=result.ticket_id,
            title=result.title,
            mode=result.mode,
            outcome=result.outcome,
            verdict=result.verdict,
            label=result.label,
            started_at=result.started_at,
            duration_ms=result.duration_ms,
            failed_step_id=failed.id if failed else None,
        )
