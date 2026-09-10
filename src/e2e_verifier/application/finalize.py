from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from e2e_verifier.application.chapters import ChapterWriter
from e2e_verifier.application.clock import Clock
from e2e_verifier.application.compiler import ExecutionPlan
from e2e_verifier.application.observations import ObservationSummarizer
from e2e_verifier.application.ports import ClosedSession, SessionObservations
from e2e_verifier.application.report import ReportBuilder
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.application.verdict import OutcomeEvaluator, SummaryComposer, VerdictPolicy
from e2e_verifier.application.video import VideoConverter
from e2e_verifier.domain.enums import Verdict
from e2e_verifier.domain.result import ArtifactSet, RunResult, StepError, StepResult
from e2e_verifier.domain.settings import Settings

VIDEO_OFFSET_UNCERTAINTY_MS = 300


@dataclass(slots=True)
class FinalizeRequest:
    plan: ExecutionPlan
    run_id: str
    run_dir: Path
    steps: list[StepResult]
    closed: ClosedSession
    observed: SessionObservations
    started_at: datetime
    run_error: StepError | None = None
    warnings: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    verdict_override: Verdict | None = None
    summary_override: str | None = None


class RunFinalizer:
    def __init__(
        self,
        store: ArtifactStore,
        clock: Clock,
        settings: Settings,
        video_converter: VideoConverter | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._converter = video_converter or VideoConverter(settings.ffmpeg_path)
        self._evaluator = OutcomeEvaluator()
        self._policy = VerdictPolicy()
        self._composer = SummaryComposer()
        self._summarizer = ObservationSummarizer()
        self._report = ReportBuilder()
        self._chapters = ChapterWriter()

    async def finish(self, request: FinalizeRequest) -> RunResult:
        plan = request.plan
        run_dir = request.run_dir
        outcome, criteria = self._evaluator.evaluate(plan, request.steps, request.run_error)
        verdict = request.verdict_override or self._policy.decide(plan.kind, plan.mode, outcome)
        observations = self._summarizer.summarize(plan, request.steps, request.observed)
        self._store.write_jsonl(run_dir / ArtifactNames.CONSOLE, request.observed.console)
        self._store.write_jsonl(run_dir / ArtifactNames.NETWORK, request.observed.network)
        warnings = [*request.warnings, *request.closed.warnings]
        mp4 = await self._convert_video(request.closed, run_dir, warnings)
        artifacts = self._artifacts(request, mp4)
        summary = request.summary_override or self._composer.compose(
            plan, verdict, request.steps, observations, request.run_error
        )
        finished_at = self._clock.now()
        result = RunResult(
            run_id=request.run_id,
            kind=plan.kind,
            ticket_id=plan.ticket_id,
            title=plan.title,
            mode=plan.mode,
            outcome=outcome,
            verdict=verdict,
            summary=summary,
            label=plan.options.label,
            started_at=request.started_at,
            finished_at=finished_at,
            duration_ms=int((finished_at - request.started_at).total_seconds() * 1000),
            video_offset_uncertainty_ms=VIDEO_OFFSET_UNCERTAINTY_MS,
            browser=request.closed.browser,
            target_url=plan.target_url,
            steps=request.steps,
            acceptance_criteria=criteria,
            observations=observations,
            artifacts=artifacts,
            warnings=warnings,
            run_error=request.run_error,
        )
        self._store.write_model(run_dir / ArtifactNames.TICKET, plan.source)
        self._store.write_model(run_dir / ArtifactNames.OPTIONS, plan.options)
        self._store.write_text(run_dir / ArtifactNames.REPORT, self._report.build(result, plan))
        self._store.write_text(run_dir / ArtifactNames.CHAPTERS, self._chapters.build(result))
        self._store.write_result(run_dir, result)
        return result

    def _artifacts(self, request: FinalizeRequest, mp4: str | None) -> ArtifactSet:
        run_dir = request.run_dir
        closed = request.closed
        popups = [self._relative(run_dir, path) for path in closed.popup_videos]
        return ArtifactSet(
            dir=str(run_dir),
            video=self._relative(run_dir, closed.video),
            video_mp4=mp4,
            trace=self._relative(run_dir, closed.trace),
            report=ArtifactNames.REPORT,
            chapters=ArtifactNames.CHAPTERS,
            console_log=ArtifactNames.CONSOLE,
            network_log=ArtifactNames.NETWORK,
            har=self._relative(run_dir, closed.har),
            screenshots=list(request.screenshots),
            popup_videos=[relative for relative in popups if relative is not None],
        )

    async def _convert_video(
        self, closed: ClosedSession, run_dir: Path, warnings: list[str]
    ) -> str | None:
        if closed.video is None or not self._converter.available:
            return None
        target = run_dir / ArtifactNames.VIDEO_MP4
        warning = await self._converter.to_mp4(closed.video, target)
        if warning is not None:
            warnings.append(warning)
            return None
        return ArtifactNames.VIDEO_MP4

    @staticmethod
    def _relative(run_dir: Path, path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return path.relative_to(run_dir).as_posix()
        except ValueError:
            return str(path)
