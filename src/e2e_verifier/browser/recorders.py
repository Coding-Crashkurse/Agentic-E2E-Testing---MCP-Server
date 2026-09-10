from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Final

from playwright.async_api import (
    BrowserContext,
    ConsoleMessage,
    Dialog,
    Download,
    Error,
    Page,
    Request,
    Response,
)

from e2e_verifier.application.ports import SessionObservations
from e2e_verifier.application.urls import UrlPattern
from e2e_verifier.domain.result import ConsoleEntry, DialogEntry, DownloadEntry, NetworkEntry

PAGE_ERROR_LEVEL: Final = "pageerror"
ERROR_LEVELS: Final = frozenset({"error", PAGE_ERROR_LEVEL})


class EntryBudget:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._used = 0
        self.dropped = 0

    def admit(self) -> bool:
        if self._used >= self._limit:
            self.dropped += 1
            return False
        self._used += 1
        return True

    @property
    def truncated(self) -> bool:
        return self.dropped > 0


class ConsoleRecorder:
    def __init__(self, offset: Callable[[], int], budget: EntryBudget) -> None:
        self._offset = offset
        self._budget = budget
        self.entries: list[ConsoleEntry] = []
        self.checkpoint_ms = 0
        self.current_step_id: str | None = None

    def attach(self, page: Page) -> None:
        page.on("console", self.on_console)
        page.on("pageerror", self.on_page_error)

    def on_console(self, message: ConsoleMessage) -> None:
        location = message.location
        where = f"{location.get('url', '')}:{location.get('lineNumber', 0)}" if location else None
        self._add(message.type, message.text, where)

    def on_page_error(self, error: Error) -> None:
        stack = error.stack or ""
        text = error.message if not stack else f"{error.message}\n{stack}"
        self._add(PAGE_ERROR_LEVEL, text, None)

    def errors_since(self, offset_ms: int, ignore_patterns: list[str]) -> list[ConsoleEntry]:
        patterns = [re.compile(pattern) for pattern in ignore_patterns]
        return [
            entry
            for entry in self.entries
            if entry.level in ERROR_LEVELS
            and entry.offset_ms >= offset_ms
            and not any(pattern.search(entry.text) for pattern in patterns)
        ]

    def matching(self, level: str | None, pattern: str) -> list[ConsoleEntry]:
        regex = re.compile(pattern)
        return [
            entry
            for entry in self.entries
            if (level is None or entry.level == level) and regex.search(entry.text)
        ]

    def _add(self, level: str, text: str, location: str | None) -> None:
        if not self._budget.admit():
            return
        self.entries.append(
            ConsoleEntry(
                offset_ms=self._offset(),
                level=level,
                text=text,
                location=location,
                step_id=self.current_step_id,
            )
        )


class NetworkRecorder:
    def __init__(self, offset: Callable[[], int], budget: EntryBudget) -> None:
        self._offset = offset
        self._budget = budget
        self.entries: list[NetworkEntry] = []
        self.current_step_id: str | None = None
        self._responses: list[tuple[NetworkEntry, Response]] = []
        self._changed = asyncio.Event()

    def attach(self, context: BrowserContext) -> None:
        context.on("request", self.on_request)
        context.on("response", self.on_response)
        context.on("requestfailed", self.on_request_failed)

    def on_request(self, request: Request) -> None:
        self._add(
            NetworkEntry(
                offset_ms=self._offset(),
                phase="request",
                method=request.method,
                url=request.url,
                resource_type=request.resource_type,
                step_id=self.current_step_id,
            )
        )

    def on_response(self, response: Response) -> None:
        entry = NetworkEntry(
            offset_ms=self._offset(),
            phase="response",
            method=response.request.method,
            url=response.url,
            status=response.status,
            resource_type=response.request.resource_type,
            step_id=self.current_step_id,
        )
        if self._add(entry):
            self._responses.append((entry, response))

    def on_request_failed(self, request: Request) -> None:
        self._add(
            NetworkEntry(
                offset_ms=self._offset(),
                phase="failed",
                method=request.method,
                url=request.url,
                resource_type=request.resource_type,
                failure_text=request.failure,
                step_id=self.current_step_id,
            )
        )

    def requests_since(
        self, offset_ms: int, method: str, pattern: UrlPattern
    ) -> list[NetworkEntry]:
        return [
            entry
            for entry in self.entries
            if entry.phase == "request"
            and entry.offset_ms >= offset_ms
            and self._method_matches(entry.method, method)
            and pattern.matches(entry.url)
        ]

    def responses_since(
        self, offset_ms: int, method: str, pattern: UrlPattern
    ) -> list[tuple[NetworkEntry, Response]]:
        return [
            (entry, response)
            for entry, response in self._responses
            if entry.offset_ms >= offset_ms
            and self._method_matches(entry.method, method)
            and pattern.matches(entry.url)
        ]

    async def wait_for[T](self, probe: Callable[[], T | None], timeout_ms: int) -> T | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_ms / 1000
        while True:
            self._changed.clear()
            found = probe()
            if found is not None:
                return found
            remaining = deadline - loop.time()
            if remaining <= 0:
                return None
            try:
                async with asyncio.timeout(remaining):
                    await self._changed.wait()
            except TimeoutError:
                return probe()

    def _add(self, entry: NetworkEntry) -> bool:
        if not self._budget.admit():
            return False
        self.entries.append(entry)
        self._changed.set()
        return True

    @staticmethod
    def _method_matches(actual: str, wanted: str) -> bool:
        return wanted == "ANY" or actual.upper() == wanted.upper()


class DialogRecorder:
    def __init__(self, offset: Callable[[], int]) -> None:
        self._offset = offset
        self.entries: list[DialogEntry] = []
        self.accept_next = True
        self.current_step_id: str | None = None

    def attach(self, page: Page) -> None:
        page.on("dialog", self.on_dialog)

    async def on_dialog(self, dialog: Dialog) -> None:
        accepted = self.accept_next
        self.entries.append(
            DialogEntry(
                offset_ms=self._offset(),
                dialog_type=dialog.type,
                message=dialog.message,
                accepted=accepted,
                step_id=self.current_step_id,
            )
        )
        if accepted:
            await dialog.accept()
        else:
            await dialog.dismiss()

    def since(self, offset_ms: int) -> list[DialogEntry]:
        return [entry for entry in self.entries if entry.offset_ms >= offset_ms]


class DownloadRecorder:
    def __init__(self, offset: Callable[[], int]) -> None:
        self._offset = offset
        self.entries: list[DownloadEntry] = []
        self.current_step_id: str | None = None

    def attach(self, page: Page) -> None:
        page.on("download", self.on_download)

    def on_download(self, download: Download) -> None:
        self.entries.append(
            DownloadEntry(
                offset_ms=self._offset(),
                suggested_filename=download.suggested_filename,
                url=download.url,
                step_id=self.current_step_id,
            )
        )

    def since(self, offset_ms: int) -> list[DownloadEntry]:
        return [entry for entry in self.entries if entry.offset_ms >= offset_ms]


class Recorders:
    def __init__(self, offset: Callable[[], int], max_entries: int) -> None:
        self._budget = EntryBudget(max_entries)
        self.console = ConsoleRecorder(offset, self._budget)
        self.network = NetworkRecorder(offset, self._budget)
        self.dialogs = DialogRecorder(offset)
        self.downloads = DownloadRecorder(offset)

    def attach_context(self, context: BrowserContext) -> None:
        self.network.attach(context)

    def attach_page(self, page: Page) -> None:
        self.console.attach(page)
        self.dialogs.attach(page)
        self.downloads.attach(page)

    def set_current_step(self, step_id: str | None) -> None:
        self.console.current_step_id = step_id
        self.network.current_step_id = step_id
        self.dialogs.current_step_id = step_id
        self.downloads.current_step_id = step_id

    def snapshot(self) -> SessionObservations:
        return SessionObservations(
            console=list(self.console.entries),
            network=list(self.network.entries),
            dialogs=list(self.dialogs.entries),
            downloads=list(self.downloads.entries),
            truncated=self._budget.truncated,
        )
