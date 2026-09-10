from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field

from e2e_verifier.application.compiler import ExecutionPlan, PlannedStep
from e2e_verifier.domain.common import StrictModel
from e2e_verifier.domain.enums import AnnotationTone, StepPhase, Verdict
from e2e_verifier.domain.result import (
    BrowserInfo,
    ConsoleEntry,
    DialogEntry,
    DownloadEntry,
    NetworkEntry,
    Rect,
    StepOutcome,
)
from e2e_verifier.domain.steps import Target


class SessionObservations(StrictModel):
    console: list[ConsoleEntry] = Field(default_factory=list)
    network: list[NetworkEntry] = Field(default_factory=list)
    dialogs: list[DialogEntry] = Field(default_factory=list)
    downloads: list[DownloadEntry] = Field(default_factory=list)
    truncated: bool = False


class ClosedSession(StrictModel):
    video: Path | None = None
    popup_videos: list[Path] = Field(default_factory=list)
    trace: Path | None = None
    har: Path | None = None
    browser: BrowserInfo
    warnings: list[str] = Field(default_factory=list)


class ProbeNavigation(StrictModel):
    status: int | None
    final_url: str
    title: str
    load_time_ms: int


class HudPort(Protocol):
    async def set_step(self, index: int, total: int, title: str, phase: StepPhase) -> None: ...

    async def mark_success(self) -> None: ...

    async def mark_failure(self, rect: Rect | None, message: str) -> None: ...

    async def mark_error(self, message: str) -> None: ...

    async def set_final(self, verdict: Verdict, message: str) -> None: ...

    async def annotate(self, rect: Rect | None, message: str, tone: AnnotationTone) -> None: ...

    async def clear_annotation(self) -> None: ...


class SessionPort(Protocol):
    @property
    def hud(self) -> HudPort: ...

    async def open(self) -> None: ...

    def offset_ms(self) -> int: ...

    async def trace_group(self, name: str) -> AbstractAsyncContextManager[Any]: ...

    async def execute(self, planned: PlannedStep, window_start_ms: int) -> StepOutcome: ...

    async def highlight_rect(self, target: Target) -> Rect | None: ...

    async def screenshot(self, path: Path, full_page: bool) -> None: ...

    async def screenshot_bytes(self, full_page: bool, jpeg_quality: int | None) -> bytes: ...

    async def page_title(self) -> str: ...

    async def close(self) -> ClosedSession: ...

    def observations(self) -> SessionObservations: ...

    def current_url(self) -> str: ...

    async def navigate_probe(self, url: str, timeout_ms: int) -> ProbeNavigation: ...

    async def aria_snapshot(self) -> str: ...

    async def discover(self, query: str | None, max_results: int) -> list[dict[str, Any]]: ...


class SessionFactoryPort(Protocol):
    def create(
        self, plan: ExecutionPlan, run_dir: Path | None, light: bool = False
    ) -> SessionPort: ...


class ProgressPort(Protocol):
    async def report(self, done: int, total: int, message: str) -> None: ...


class NullProgress:
    async def report(self, done: int, total: int, message: str) -> None:
        return None
