from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from e2e_verifier.application.clock import SystemClock
from e2e_verifier.application.compiler import PlanCompiler
from e2e_verifier.application.exploration import ElementDiscovery, TargetProbe
from e2e_verifier.application.finalize import RunFinalizer
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.interactive import SessionManager
from e2e_verifier.application.registry import RunRegistry
from e2e_verifier.application.runner import ScenarioRunner
from e2e_verifier.application.store import ArtifactStore, RetentionPolicy
from e2e_verifier.application.validation import TicketValidator
from e2e_verifier.browser.executors.registry import DefaultStepRegistry
from e2e_verifier.browser.session import BrowserPool, BrowserSessionFactory
from e2e_verifier.domain.settings import Settings
from e2e_verifier.server.prompts import VerifierPrompts
from e2e_verifier.server.resources import RunResources
from e2e_verifier.server.session_tools import SessionTools
from e2e_verifier.server.tools import VerifierTools
from e2e_verifier.server.versions import VersionInfo

SERVER_NAME = "e2e-verifier"
INSTRUCTIONS = (
    "e2e-verifier lets an agent operate a website in a real, recorded browser and turns bug "
    "tickets into evidence (annotated video, Playwright trace, screenshots, logs, report). "
    "Two ways of working: (1) interactive - session_open(url), then session_act with one step at "
    "a time (click, fill, expect_visible, ...), session_inspect to read the page, "
    "session_annotate to mark findings in the video, session_close to get the artifacts; "
    "(2) batch - build a BugTicket (prompt ticket_from_report, discover_elements for targets), "
    "validate_ticket, then run_ticket with mode=reproduce before a fix and mode=verify after it. "
    "probe_target checks that the site is up. Fetch artifacts with get_artifact or the "
    "runs://{run_id}/... resources; a session id is also a run id."
)


class PoolLifespan:
    def __init__(self, pool: BrowserPool, sessions: SessionManager) -> None:
        self._pool = pool
        self._sessions = sessions

    @asynccontextmanager
    async def __call__(self, server: FastMCP[Any]) -> AsyncIterator[dict[str, Any]]:
        await self._pool.start()
        try:
            yield {}
        finally:
            await self._sessions.close_all()
            await self._pool.stop()


class ServerFactory:
    def __init__(self, settings: Settings, pool: BrowserPool | None = None) -> None:
        self._settings = settings
        self.pool = pool or BrowserPool()
        self.clock = SystemClock()
        self.store = ArtifactStore(settings.artifact_dir)
        self.allowlist = HostAllowlist(settings.allowed_hosts, settings.allow_any_host)
        self.registry = DefaultStepRegistry()
        self.sessions = BrowserSessionFactory(
            self.pool, settings, self.clock, self.registry, self.allowlist
        )
        self.compiler = PlanCompiler(settings)
        self.validator = TicketValidator(settings, self.allowlist)
        self.finalizer = RunFinalizer(self.store, self.clock, settings)
        self.runner = ScenarioRunner(
            self.sessions, self.store, self.clock, settings, finalizer=self.finalizer
        )
        self.runs = RunRegistry(self.store)
        self.retention = RetentionPolicy(
            settings.max_runs_retained, settings.max_artifact_age_h, self.clock
        )
        self.probe = TargetProbe(self.sessions, self.compiler, self.allowlist, settings)
        self.discovery = ElementDiscovery(self.sessions, self.compiler, self.allowlist, settings)
        self.interactive = SessionManager(
            self.sessions,
            self.compiler,
            self.store,
            self.runs,
            self.finalizer,
            self.clock,
            settings,
            self.allowlist,
        )
        self.versions = VersionInfo.detect()

    def build(self) -> FastMCP[Any]:
        mcp: FastMCP[Any] = FastMCP(
            name=SERVER_NAME,
            instructions=INSTRUCTIONS,
            version=self.versions.server,
            lifespan=PoolLifespan(self.pool, self.interactive),
        )
        SessionTools(self.interactive, self._settings).register(mcp)
        VerifierTools(
            settings=self._settings,
            store=self.store,
            runs=self.runs,
            compiler=self.compiler,
            validator=self.validator,
            runner=self.runner,
            probe=self.probe,
            discovery=self.discovery,
            retention=self.retention,
            allowlist=self.allowlist,
            versions=self.versions,
        ).register(mcp)
        RunResources(self.store, self.runs, self._settings).register(mcp)
        VerifierPrompts(self.store, self.runs).register(mcp)
        return mcp
