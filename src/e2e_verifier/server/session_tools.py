from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from playwright.async_api import Error as PlaywrightError

from e2e_verifier.application.interactive import InteractiveSession, SessionManager
from e2e_verifier.domain.enums import AnnotationTone, Verdict
from e2e_verifier.domain.errors import VerifierError
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.result import DiscoveryResult, RunResult, SessionInfo, SessionOpened
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import Step, Target

MAX_INSPECT_RESULTS = 100


class SessionTools:
    def __init__(self, manager: SessionManager, settings: Settings) -> None:
        self._manager = manager
        self._settings = settings

    def register(self, mcp: FastMCP[Any]) -> None:
        mcp.tool(
            self.session_open,
            name="session_open",
            description=(
                "Open an interactive, recorded browser session on a URL and return its id, the "
                "result of the first navigation and a screenshot. Everything that happens in the "
                "session is recorded as video, trace, screenshots and logs until session_close. "
                "Use session_act to drive the page step by step."
            ),
            output_schema=None,
        )
        mcp.tool(
            self.session_act,
            name="session_act",
            description=(
                "Execute one step in an open session and return the step result plus a screenshot. "
                "A step is any action or assertion from the ticket schema, for example "
                '{"id": "s1", "action": "click", "target": {"role": {"role": "button", '
                '"name": "Save"}}} or {"id": "s2", "action": "expect_visible", "target": '
                '{"test_id": "toast"}}. Failed assertions do not end the session; they are marked '
                'in the video with a red frame. Call get_schema(kind="step") for all step types.'
            ),
            output_schema=None,
        )
        mcp.tool(
            self.session_annotate,
            name="session_annotate",
            description=(
                "Draw an annotation into the recorded video: a callout with your message, "
                "optionally with a frame around a target element (tone info, success or failure). "
                "The annotation stays visible for hold_ms and is captured as a screenshot."
            ),
            output_schema=None,
        )
        mcp.tool(
            self.session_screenshot,
            name="session_screenshot",
            description=(
                "Take a screenshot of the current page of an open session (viewport or full page)."
            ),
            output_schema=None,
        )
        mcp.tool(
            self.session_inspect,
            name="session_inspect",
            description=(
                "Inspect the current page of an open session without changing it: ARIA snapshot "
                "plus candidate targets matching a query, each with a suggested Target."
            ),
        )
        mcp.tool(
            self.session_close,
            name="session_close",
            description=(
                "Close an open session, stop the recording and write video.webm, trace.zip, "
                "report.md, chapters.vtt and result.json. Optionally pass your own verdict "
                "(reproduced, not_reproduced, fixed, still_broken, passed, failed, inconclusive) "
                "and summary; otherwise they are derived from the executed assertions. Fetch "
                "artifacts with get_artifact using the session id as run_id."
            ),
        )
        mcp.tool(
            self.session_list,
            name="session_list",
            description="List open interactive sessions.",
        )

    async def session_open(self, url: str, options: RunOptions | None = None) -> list[Any]:
        interactive, first = await self._call(self._manager.open(url, options))
        payload = SessionOpened(session=interactive.info(), first_step=first)
        return [payload.model_dump_json(indent=2), await self._image(interactive)]

    async def session_act(
        self, session_id: str, step: Step, include_screenshot: bool = True
    ) -> str | list[Any]:
        interactive = self._session(session_id)
        async with interactive.lock:
            result = await self._call(interactive.act(step))
            text = result.model_dump_json(indent=2)
            if not include_screenshot:
                return text
            return [text, await self._image(interactive)]

    async def session_annotate(
        self,
        session_id: str,
        message: str,
        target: Target | None = None,
        tone: AnnotationTone = AnnotationTone.INFO,
        hold_ms: int = 1500,
    ) -> list[Any]:
        interactive = self._session(session_id)
        async with interactive.lock:
            result = await self._call(interactive.annotate(message, target, tone, hold_ms))
            return [result.model_dump_json(indent=2), await self._image(interactive)]

    async def session_screenshot(self, session_id: str, full_page: bool = False) -> list[Any]:
        interactive = self._session(session_id)
        async with interactive.lock:
            saved = await self._call(interactive.screenshot(full_page))
            image = await self._image(interactive)
        return [f"saved as {saved}" if saved else "screenshot could not be saved", image]

    async def session_inspect(
        self, session_id: str, query: str | None = None, max_results: int = 20
    ) -> DiscoveryResult:
        interactive = self._session(session_id)
        limit = max(1, min(max_results, MAX_INSPECT_RESULTS))
        async with interactive.lock:
            return await self._call(interactive.inspect(query, limit))

    async def session_close(
        self, session_id: str, verdict: Verdict | None = None, summary: str | None = None
    ) -> RunResult:
        return await self._call(self._manager.close(session_id, verdict, summary))

    async def session_list(self) -> list[SessionInfo]:
        await self._manager.reap_idle()
        return self._manager.list_open()

    def _session(self, session_id: str) -> InteractiveSession:
        try:
            return self._manager.get(session_id)
        except VerifierError as exc:
            raise ToolError(str(exc)) from exc

    @staticmethod
    async def _call[T](call: Awaitable[T]) -> T:
        try:
            return await call
        except (VerifierError, PlaywrightError) as exc:
            raise ToolError(str(exc)) from exc

    @staticmethod
    async def _image(interactive: InteractiveSession) -> Image:
        try:
            data = await interactive.inline_screenshot()
        except (VerifierError, PlaywrightError) as exc:
            raise ToolError(f"screenshot failed: {exc}") from exc
        return Image(data=data, format="jpeg")
