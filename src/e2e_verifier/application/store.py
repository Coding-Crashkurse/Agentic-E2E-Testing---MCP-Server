from __future__ import annotations

import re
import shutil
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final

from pydantic import BaseModel
from ulid import ULID

from e2e_verifier.application.clock import Clock
from e2e_verifier.domain.common import RUN_ID_PATTERN, FrozenModel
from e2e_verifier.domain.enums import ArtifactKind
from e2e_verifier.domain.errors import ArtifactNotFoundError, InvalidRunIdError, RunNotFoundError
from e2e_verifier.domain.result import RunResult

RUN_ID_REGEX: Final = re.compile(RUN_ID_PATTERN)


class ArtifactNames:
    TICKET: Final = "ticket.json"
    OPTIONS: Final = "options.json"
    RESULT: Final = "result.json"
    REPORT: Final = "report.md"
    VIDEO: Final = "video.webm"
    VIDEO_MP4: Final = "video.mp4"
    TRACE: Final = "trace.zip"
    CHAPTERS: Final = "chapters.vtt"
    CONSOLE: Final = "console.jsonl"
    NETWORK: Final = "network.jsonl"
    HAR: Final = "network.har"
    SCREENSHOTS: Final = "screenshots"
    VIDEO_RAW: Final = "video_raw"

    FILES_BY_KIND: Final[dict[ArtifactKind, str]] = {
        ArtifactKind.TICKET: TICKET,
        ArtifactKind.RESULT: RESULT,
        ArtifactKind.REPORT: REPORT,
        ArtifactKind.VIDEO: VIDEO,
        ArtifactKind.VIDEO_MP4: VIDEO_MP4,
        ArtifactKind.TRACE: TRACE,
        ArtifactKind.CHAPTERS: CHAPTERS,
        ArtifactKind.CONSOLE_LOG: CONSOLE,
        ArtifactKind.NETWORK_LOG: NETWORK,
        ArtifactKind.HAR: HAR,
    }

    MIME_BY_KIND: Final[dict[ArtifactKind, str]] = {
        ArtifactKind.TICKET: "application/json",
        ArtifactKind.RESULT: "application/json",
        ArtifactKind.REPORT: "text/markdown",
        ArtifactKind.VIDEO: "video/webm",
        ArtifactKind.VIDEO_MP4: "video/mp4",
        ArtifactKind.TRACE: "application/zip",
        ArtifactKind.CHAPTERS: "text/vtt",
        ArtifactKind.CONSOLE_LOG: "application/x-ndjson",
        ArtifactKind.NETWORK_LOG: "application/x-ndjson",
        ArtifactKind.HAR: "application/json",
        ArtifactKind.SCREENSHOT: "image/png",
    }


class RunLocation(FrozenModel):
    run_id: str
    path: Path


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self._runs = root / "runs"

    @property
    def runs_root(self) -> Path:
        return self._runs

    def create_run(self) -> RunLocation:
        run_id = str(ULID())
        path = self._runs / run_id
        (path / ArtifactNames.SCREENSHOTS).mkdir(parents=True, exist_ok=False)
        return RunLocation(run_id=run_id, path=path)

    @staticmethod
    def validate_id(run_id: str) -> str:
        if not RUN_ID_REGEX.fullmatch(run_id):
            raise InvalidRunIdError(run_id)
        return run_id

    def run_dir(self, run_id: str) -> Path:
        path = self._runs / self.validate_id(run_id)
        if not path.is_dir():
            raise RunNotFoundError(run_id)
        return path

    def exists(self, run_id: str) -> bool:
        return (self._runs / self.validate_id(run_id)).is_dir()

    def is_complete(self, run_id: str) -> bool:
        return (self._runs / self.validate_id(run_id) / ArtifactNames.RESULT).is_file()

    def list_run_ids(self) -> list[str]:
        if not self._runs.is_dir():
            return []
        ids = [entry.name for entry in self._runs.iterdir() if entry.is_dir()]
        return sorted((run_id for run_id in ids if RUN_ID_REGEX.fullmatch(run_id)), reverse=True)

    def read_result(self, run_id: str) -> RunResult:
        path = self.run_dir(run_id) / ArtifactNames.RESULT
        if not path.is_file():
            raise RunNotFoundError(run_id)
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))

    def write_result(self, run_dir: Path, result: RunResult) -> Path:
        target = run_dir / ArtifactNames.RESULT
        temporary = run_dir / f"{ArtifactNames.RESULT}.tmp"
        temporary.write_text(result.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
        temporary.replace(target)
        return target

    @staticmethod
    def write_model(path: Path, model: BaseModel) -> None:
        path.write_text(model.model_dump_json(indent=2, by_alias=True), encoding="utf-8")

    @staticmethod
    def write_jsonl(path: Path, models: Iterable[BaseModel]) -> None:
        lines = [model.model_dump_json(by_alias=True) for model in models]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    @staticmethod
    def write_text(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def delete(self, run_id: str) -> None:
        shutil.rmtree(self.run_dir(run_id))

    def artifact_path(self, run_id: str, kind: ArtifactKind, index: int | None = None) -> Path:
        run_dir = self.run_dir(run_id)
        if kind is ArtifactKind.SCREENSHOT:
            return self._screenshot_path(run_id, run_dir, index)
        path = run_dir / ArtifactNames.FILES_BY_KIND[kind]
        if not path.is_file():
            raise ArtifactNotFoundError(run_id, path.name)
        return path

    def screenshots(self, run_dir: Path) -> list[Path]:
        folder = run_dir / ArtifactNames.SCREENSHOTS
        if not folder.is_dir():
            return []
        return sorted(entry for entry in folder.iterdir() if entry.suffix == ".png")

    def _screenshot_path(self, run_id: str, run_dir: Path, index: int | None) -> Path:
        shots = self.screenshots(run_dir)
        position = index or 0
        if position < 0 or position >= len(shots):
            raise ArtifactNotFoundError(run_id, f"screenshot #{position}")
        return shots[position]

    @staticmethod
    def created_at(run_id: str) -> datetime:
        return ULID.from_str(run_id).datetime


class RetentionPolicy:
    def __init__(self, max_runs: int, max_age_hours: int, clock: Clock) -> None:
        self._max_runs = max_runs
        self._max_age = timedelta(hours=max_age_hours)
        self._clock = clock

    def apply(self, store: ArtifactStore, protected: set[str]) -> list[str]:
        deleted: list[str] = []
        now = self._clock.now()
        candidates = [run_id for run_id in store.list_run_ids() if run_id not in protected]
        for position, run_id in enumerate(candidates):
            too_many = position >= self._max_runs
            too_old = now - store.created_at(run_id) > self._max_age
            if too_many or too_old:
                store.delete(run_id)
                deleted.append(run_id)
        return deleted
