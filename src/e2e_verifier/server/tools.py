from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File
from playwright.async_api import Error as PlaywrightError
from pydantic import BaseModel, TypeAdapter

from e2e_verifier.application.compiler import PlanCompiler
from e2e_verifier.application.exploration import ElementDiscovery, TargetProbe
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.registry import RunRegistry
from e2e_verifier.application.runner import ScenarioRunner
from e2e_verifier.application.store import ArtifactNames, ArtifactStore, RetentionPolicy
from e2e_verifier.application.validation import TicketValidator
from e2e_verifier.domain.enums import ArtifactKind, Outcome, SchemaKind
from e2e_verifier.domain.errors import VerifierError
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import (
    ArtifactLocation,
    DeleteResult,
    DiscoveryResult,
    ProbeResult,
    RunResult,
    RunSummary,
    ServerInfo,
    ValidationReport,
)
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import Step
from e2e_verifier.domain.ticket import BugTicket, Scenario
from e2e_verifier.server.versions import VersionInfo

MAX_LIST_LIMIT = 200
MAX_DISCOVERY_RESULTS = 100


class ContextProgress:
    def __init__(self, ctx: Context | None) -> None:
        self._ctx = ctx

    async def report(self, done: int, total: int, message: str) -> None:
        if self._ctx is None:
            return
        await self._ctx.report_progress(done, total, message)
        await self._ctx.info(message)


class VerifierTools:
    def __init__(
        self,
        settings: Settings,
        store: ArtifactStore,
        runs: RunRegistry,
        compiler: PlanCompiler,
        validator: TicketValidator,
        runner: ScenarioRunner,
        probe: TargetProbe,
        discovery: ElementDiscovery,
        retention: RetentionPolicy,
        allowlist: HostAllowlist,
        versions: VersionInfo,
    ) -> None:
        self._settings = settings
        self._store = store
        self._runs = runs
        self._compiler = compiler
        self._validator = validator
        self._runner = runner
        self._probe = probe
        self._discovery = discovery
        self._retention = retention
        self._allowlist = allowlist
        self._versions = versions
        self._semaphore = asyncio.Semaphore(settings.max_parallel_runs)

    def register(self, mcp: FastMCP[Any]) -> None:
        mcp.tool(
            self.get_schema,
            name="get_schema",
            description=(
                "Return the JSON schema for a BugTicket, Scenario, RunOptions or RunResult."
            ),
        )
        mcp.tool(
            self.validate_ticket,
            name="validate_ticket",
            description="Validate a ticket without opening a browser; returns errors and warnings.",
        )
        mcp.tool(
            self.run_ticket,
            name="run_ticket",
            description=(
                "Execute a BugTicket in a real browser. Records an annotated video, a Playwright "
                "trace, screenshots and logs, then returns the verdict per acceptance criterion. "
                "Use mode=reproduce before a fix and mode=verify after it."
            ),
        )
        mcp.tool(
            self.run_scenario,
            name="run_scenario",
            description="Execute a Scenario (steps without bug semantics) and record artifacts.",
        )
        mcp.tool(
            self.get_run,
            name="get_run",
            description="Return the stored RunResult of a finished run.",
        )
        mcp.tool(
            self.list_runs,
            name="list_runs",
            description=(
                "List finished runs, newest first, optionally filtered by ticket or outcome."
            ),
        )
        mcp.tool(
            self.get_artifact,
            name="get_artifact",
            description=(
                "Fetch one artifact of a run (video, trace, report, screenshot, logs). Small files "
                "are returned inline, large ones as a path."
            ),
            output_schema=None,
        )
        mcp.tool(
            self.delete_run,
            name="delete_run",
            description="Delete a finished run and all of its artifacts.",
        )
        mcp.tool(
            self.probe_target,
            name="probe_target",
            description="Open a URL once and report status, title, load time and console errors.",
        )
        mcp.tool(
            self.discover_elements,
            name="discover_elements",
            description=(
                "Inspect a page: returns the ARIA snapshot and candidate targets matching a query, "
                "each with a suggested Target for tickets. steps_before can log in or navigate "
                "first."
            ),
        )
        mcp.tool(
            self.server_info,
            name="server_info",
            description="Versions, configuration and run counts of this server.",
        )

    async def get_schema(self, kind: SchemaKind) -> dict[str, Any]:
        if kind is SchemaKind.STEP:
            return TypeAdapter(Step).json_schema(by_alias=True)
        models: dict[SchemaKind, type[BaseModel]] = {
            SchemaKind.TICKET: BugTicket,
            SchemaKind.SCENARIO: Scenario,
            SchemaKind.RUN_OPTIONS: RunOptions,
            SchemaKind.RUN_RESULT: RunResult,
        }
        return models[kind].model_json_schema(by_alias=True)

    async def validate_ticket(
        self, ticket: BugTicket, options: RunOptions | None = None
    ) -> ValidationReport:
        return self._validator.validate(ticket, options)

    async def run_ticket(
        self, ticket: BugTicket, ctx: Context, options: RunOptions | None = None
    ) -> RunResult:
        return await self._run(ticket, options, ctx)

    async def run_scenario(
        self, scenario: Scenario, ctx: Context, options: RunOptions | None = None
    ) -> RunResult:
        return await self._run(scenario, options, ctx)

    async def get_run(self, run_id: str) -> RunResult:
        return self._guard(lambda: self._runs.get(run_id))

    async def list_runs(
        self, limit: int = 20, ticket_id: str | None = None, outcome: Outcome | None = None
    ) -> list[RunSummary]:
        return self._runs.list(max(1, min(limit, MAX_LIST_LIMIT)), ticket_id, outcome)

    async def get_artifact(
        self, run_id: str, kind: ArtifactKind, index: int | None = None
    ) -> File | ArtifactLocation:
        path = self._guard(lambda: self._store.artifact_path(run_id, kind, index))
        size = path.stat().st_size
        if size > self._settings.max_inline_artifact_bytes:
            return ArtifactLocation(
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
        return File(
            data=path.read_bytes(),
            format=path.suffix.lstrip("."),
            name=path.stem,
        )

    async def delete_run(self, run_id: str) -> DeleteResult:
        if self._runs.is_running(run_id):
            raise ToolError(f"Run {run_id} is still in progress")
        self._guard(lambda: self._store.delete(run_id))
        return DeleteResult(run_id=run_id, deleted=True)

    async def probe_target(self, url: str) -> ProbeResult:
        try:
            return await self._probe.probe(url)
        except (VerifierError, PlaywrightError) as exc:
            raise ToolError(str(exc)) from exc

    async def discover_elements(
        self,
        url: str,
        query: str | None = None,
        steps_before: list[Step] | None = None,
        max_results: int = 20,
    ) -> DiscoveryResult:
        limit = max(1, min(max_results, MAX_DISCOVERY_RESULTS))
        try:
            return await self._discovery.discover(url, query, steps_before, limit)
        except (VerifierError, PlaywrightError) as exc:
            raise ToolError(str(exc)) from exc

    async def server_info(self) -> ServerInfo:
        return ServerInfo(
            server_version=self._versions.server,
            fastmcp_version=self._versions.fastmcp,
            playwright_version=self._versions.playwright,
            default_browser=self._settings.browser,
            headless=self._settings.headless,
            artifact_dir=str(self._store.runs_root.parent.resolve()),
            allowed_hosts=self._allowlist.patterns,
            allow_any_host=self._allowlist.allow_any,
            max_parallel_runs=self._settings.max_parallel_runs,
            runs_stored=self._runs.count(),
            runs_in_progress=len(self._runs.running_ids),
        )

    async def _run(
        self, source: BugTicket | Scenario, options: RunOptions | None, ctx: Context | None
    ) -> RunResult:
        report = self._validator.validate(source, options)
        if not report.ok:
            raise ToolError("Ticket validation failed: " + self._format_issues(report))
        for warning in report.warnings:
            if ctx is not None:
                await ctx.warning(f"[{warning.code}] {warning.message}")
        plan = self._compiler.compile(source, options)
        location = self._store.create_run()
        self._runs.mark_running(location.run_id)
        try:
            async with self._semaphore:
                result = await self._runner.run(
                    plan, location.run_id, location.path, ContextProgress(ctx)
                )
        finally:
            self._runs.mark_finished(location.run_id)
        self._retention.apply(self._store, self._runs.running_ids | {location.run_id})
        return result

    @staticmethod
    def _format_issues(report: ValidationReport) -> str:
        parts = []
        for issue in report.errors:
            where = f" (step {issue.step_id})" if issue.step_id else ""
            parts.append(f"[{issue.code}] {issue.message}{where}")
        return "; ".join(parts)

    @staticmethod
    def _guard[T](call: Callable[[], T]) -> T:
        try:
            return call()
        except VerifierError as exc:
            raise ToolError(str(exc)) from exc

    @property
    def artifact_names(self) -> type[ArtifactNames]:
        return ArtifactNames
