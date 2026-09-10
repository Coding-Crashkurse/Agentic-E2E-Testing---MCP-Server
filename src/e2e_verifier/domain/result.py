from __future__ import annotations

from datetime import datetime

from pydantic import Field

from e2e_verifier.domain.common import StrictModel
from e2e_verifier.domain.enums import (
    CriterionStatus,
    ErrorCategory,
    HighlightSource,
    Outcome,
    RunKind,
    RunMode,
    StepPhase,
    StepStatus,
    Verdict,
)
from e2e_verifier.domain.steps import Target
from e2e_verifier.domain.ticket import Viewport


class Rect(StrictModel):
    x: float
    y: float
    width: float
    height: float


class HighlightTarget(StrictModel):
    source: HighlightSource
    step_id: str
    rect: Rect | None


class StepError(StrictModel):
    category: ErrorCategory
    message: str
    locator: str | None = None
    highlight_target: HighlightTarget | None = None
    candidates: list[str] = Field(default_factory=list)


class StepOutcome(StrictModel):
    status: StepStatus
    error: StepError | None = None

    @classmethod
    def passed(cls) -> StepOutcome:
        return cls(status=StepStatus.PASSED)

    @classmethod
    def failed(
        cls, category: ErrorCategory, message: str, locator: str | None = None
    ) -> StepOutcome:
        return cls(
            status=StepStatus.FAILED,
            error=StepError(category=category, message=message, locator=locator),
        )

    @classmethod
    def errored(
        cls, category: ErrorCategory, message: str, locator: str | None = None
    ) -> StepOutcome:
        return cls(
            status=StepStatus.ERROR,
            error=StepError(category=category, message=message, locator=locator),
        )


class StepResult(StrictModel):
    index: int
    id: str
    phase: StepPhase
    action: str
    title: str
    status: StepStatus
    started_offset_ms: int | None = None
    ended_offset_ms: int | None = None
    error: StepError | None = None
    screenshot: str | None = None
    failure_screenshot: str | None = None
    trace_group: str | None = None

    @property
    def duration_ms(self) -> int | None:
        if self.started_offset_ms is None or self.ended_offset_ms is None:
            return None
        return self.ended_offset_ms - self.started_offset_ms


class CriterionEvidence(StrictModel):
    step_id: str
    video_offset_ms: int | None
    screenshot: str | None
    trace_group: str | None


class CriterionResult(StrictModel):
    id: str
    description: str
    status: CriterionStatus
    step_ids: list[str]
    evidence: CriterionEvidence | None = None


class ConsoleEntry(StrictModel):
    offset_ms: int
    level: str
    text: str
    location: str | None = None
    step_id: str | None = None


class NetworkEntry(StrictModel):
    offset_ms: int
    phase: str
    method: str
    url: str
    status: int | None = None
    resource_type: str | None = None
    failure_text: str | None = None
    step_id: str | None = None


class DialogEntry(StrictModel):
    offset_ms: int
    dialog_type: str
    message: str
    accepted: bool
    step_id: str | None = None


class DownloadEntry(StrictModel):
    offset_ms: int
    suggested_filename: str
    url: str
    step_id: str | None = None


class Observations(StrictModel):
    console_errors: int
    page_errors: int
    failed_requests: int
    requests_total: int
    requests_after_step: dict[str, int]
    dialogs: int = 0
    downloads: int = 0
    truncated: bool = False


class ArtifactSet(StrictModel):
    dir: str
    video: str | None
    video_mp4: str | None
    trace: str | None
    report: str | None
    chapters: str | None
    console_log: str | None
    network_log: str | None
    har: str | None
    screenshots: list[str]
    popup_videos: list[str] = Field(default_factory=list)


class BrowserInfo(StrictModel):
    name: str
    version: str | None
    headless: bool
    viewport: Viewport


class RunResult(StrictModel):
    run_id: str
    kind: RunKind
    ticket_id: str
    title: str
    mode: RunMode
    outcome: Outcome
    verdict: Verdict
    summary: str
    label: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    video_offset_uncertainty_ms: int
    browser: BrowserInfo
    target_url: str
    steps: list[StepResult]
    acceptance_criteria: list[CriterionResult]
    observations: Observations
    artifacts: ArtifactSet
    warnings: list[str] = Field(default_factory=list)
    run_error: StepError | None = None

    def first_failure(self) -> StepResult | None:
        return next((step for step in self.steps if step.status is StepStatus.FAILED), None)

    def first_error(self) -> StepResult | None:
        return next((step for step in self.steps if step.status is StepStatus.ERROR), None)


class RunSummary(StrictModel):
    run_id: str
    kind: RunKind
    ticket_id: str
    title: str
    mode: RunMode
    outcome: Outcome
    verdict: Verdict
    label: str | None
    started_at: datetime
    duration_ms: int
    failed_step_id: str | None


class ValidationIssue(StrictModel):
    code: str
    message: str
    step_id: str | None = None


class ValidationReport(StrictModel):
    ok: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]


class ProbeResult(StrictModel):
    url: str
    final_url: str | None
    reachable: bool
    status: int | None
    title: str | None
    load_time_ms: int | None
    console_errors: list[str]
    page_errors: list[str]
    error: str | None


class ElementCandidate(StrictModel):
    tag: str
    role: str | None
    name: str | None
    test_id: str | None
    element_id: str | None
    css: str
    visible: bool
    disabled: bool
    rect: Rect
    suggested_target: Target


class DiscoveryResult(StrictModel):
    url: str
    final_url: str
    query: str | None
    candidates: list[ElementCandidate]
    aria_snapshot: str
    aria_snapshot_truncated: bool


class ServerInfo(StrictModel):
    server_version: str
    fastmcp_version: str
    playwright_version: str
    default_browser: str
    headless: bool
    artifact_dir: str
    allowed_hosts: list[str]
    allow_any_host: bool
    max_parallel_runs: int
    runs_stored: int
    runs_in_progress: int


class ArtifactLocation(StrictModel):
    run_id: str
    kind: str
    path: str
    size_bytes: int
    inline: bool = False
    reason: str | None = None


class DeleteResult(StrictModel):
    run_id: str
    deleted: bool


class SessionInfo(StrictModel):
    session_id: str
    label: str
    url: str
    title: str
    steps_executed: int
    failed_steps: int
    annotations: int
    opened_at: datetime
    idle_seconds: int
    artifacts_dir: str


class ActResult(StrictModel):
    session_id: str
    step: StepResult
    url: str
    title: str
    screenshot: str | None
    new_console_errors: list[str] = Field(default_factory=list)
    new_page_errors: list[str] = Field(default_factory=list)
    new_requests: int = 0
    hint: str | None = None


class AnnotationResult(StrictModel):
    session_id: str
    index: int
    message: str
    tone: str
    rect: Rect | None
    screenshot: str | None


class SessionOpened(StrictModel):
    session: SessionInfo
    first_step: ActResult
