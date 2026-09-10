from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError

from e2e_verifier.application.registry import RunRegistry
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.domain.enums import ArtifactKind
from e2e_verifier.domain.errors import VerifierError
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import ArtifactLocation, RunResult
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import BugTicket, Scenario


class RunResources:
    def __init__(self, store: ArtifactStore, runs: RunRegistry, settings: Settings) -> None:
        self._store = store
        self._runs = runs
        self._settings = settings

    def register(self, mcp: FastMCP[Any]) -> None:
        schemas = {
            "schema://ticket": ("ticket_schema", "JSON schema of BugTicket", self.ticket_schema),
            "schema://scenario": (
                "scenario_schema",
                "JSON schema of Scenario",
                self.scenario_schema,
            ),
            "schema://run-options": (
                "run_options_schema",
                "JSON schema of RunOptions",
                self.run_options_schema,
            ),
            "schema://run-result": (
                "run_result_schema",
                "JSON schema of RunResult",
                self.run_result_schema,
            ),
        }
        for uri, (name, description, handler) in schemas.items():
            mcp.resource(uri, name=name, description=description, mime_type="application/json")(
                handler
            )
        mcp.resource(
            "runs://index",
            name="runs_index",
            description="All finished runs, newest first",
            mime_type="application/json",
        )(self.index)
        binaries = {
            "result": (ArtifactKind.RESULT, "result.json of a run"),
            "ticket": (ArtifactKind.TICKET, "ticket.json as received (secrets masked)"),
            "report": (ArtifactKind.REPORT, "Markdown report of a run"),
            "video": (ArtifactKind.VIDEO, "Annotated video (webm)"),
            "trace": (ArtifactKind.TRACE, "Playwright trace.zip"),
            "console": (ArtifactKind.CONSOLE_LOG, "Console log (ndjson)"),
            "network": (ArtifactKind.NETWORK_LOG, "Network log (ndjson)"),
            "chapters": (ArtifactKind.CHAPTERS, "WebVTT chapters of the video"),
            "har": (ArtifactKind.HAR, "HAR file when record_har was enabled"),
        }
        for suffix, (kind, description) in binaries.items():
            mcp.resource(
                f"runs://{{run_id}}/{suffix}",
                name=f"run_{suffix}",
                description=description,
                mime_type=ArtifactNames.MIME_BY_KIND[kind],
            )(self._artifact_handler(kind))
        mcp.resource(
            "runs://{run_id}/screenshots/{index}",
            name="run_screenshot",
            description="Screenshot number index (zero-based) of a run",
            mime_type="image/png",
        )(self.screenshot)

    async def ticket_schema(self) -> str:
        return json.dumps(BugTicket.model_json_schema(by_alias=True), indent=2)

    async def scenario_schema(self) -> str:
        return json.dumps(Scenario.model_json_schema(by_alias=True), indent=2)

    async def run_options_schema(self) -> str:
        return json.dumps(RunOptions.model_json_schema(by_alias=True), indent=2)

    async def run_result_schema(self) -> str:
        return json.dumps(RunResult.model_json_schema(by_alias=True), indent=2)

    async def index(self) -> str:
        summaries = self._runs.list(self._settings.max_runs_retained)
        return json.dumps([summary.model_dump(mode="json") for summary in summaries], indent=2)

    async def screenshot(self, run_id: str, index: int) -> bytes | str:
        return self._read(run_id, ArtifactKind.SCREENSHOT, index)

    def _artifact_handler(self, kind: ArtifactKind) -> Any:
        async def handler(run_id: str) -> bytes | str:
            return self._read(run_id, kind, None)

        return handler

    def _read(self, run_id: str, kind: ArtifactKind, index: int | None) -> bytes | str:
        try:
            path = self._store.artifact_path(run_id, kind, index)
        except VerifierError as exc:
            raise ResourceError(str(exc)) from exc
        size = path.stat().st_size
        if size > self._settings.max_inline_artifact_bytes:
            location = ArtifactLocation(
                run_id=run_id,
                kind=kind,
                path=str(path),
                size_bytes=size,
                inline=False,
                reason=(
                    "larger than E2E_MAX_INLINE_ARTIFACT_MB="
                    f"{self._settings.max_inline_artifact_mb}"
                ),
            )
            return location.model_dump_json(indent=2)
        if kind in {
            ArtifactKind.RESULT,
            ArtifactKind.TICKET,
            ArtifactKind.REPORT,
            ArtifactKind.CONSOLE_LOG,
            ArtifactKind.NETWORK_LOG,
            ArtifactKind.CHAPTERS,
            ArtifactKind.HAR,
        }:
            return path.read_text(encoding="utf-8")
        return path.read_bytes()
