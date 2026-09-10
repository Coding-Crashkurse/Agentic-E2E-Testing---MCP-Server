from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from e2e_verifier.domain.common import StrictModel
from e2e_verifier.domain.enums import AnnotationTone, StepPhase, Verdict
from e2e_verifier.domain.result import Rect

SET_STATE_SCRIPT = (
    "(state) => { const hud = window.__e2eHud; if (hud) { hud.setState(state); } "
    "return Boolean(hud); }"
)
GET_STATE_SCRIPT = "() => (window.__e2eHud ? window.__e2eHud.getState() : null)"


class HudStep(StrictModel):
    index: int
    total: int
    title: str
    phase: StepPhase
    status: str = "running"


class HudFailure(StrictModel):
    rect: Rect | None
    message: str


class HudFinal(StrictModel):
    verdict: Verdict
    message: str


class HudAnnotation(StrictModel):
    rect: Rect | None
    message: str
    tone: AnnotationTone


class HudState(StrictModel):
    enabled: bool = True
    ticket_id: str = ""
    mode: str = "verify"
    language: str = "en"
    position: str = "top"
    show_timer: bool = True
    show_ticket_id: bool = True
    started_at_ms: int = 0
    step: HudStep | None = None
    failure: HudFailure | None = None
    final: HudFinal | None = None
    annotation: HudAnnotation | None = None


class HudController:
    def __init__(self, page_provider: Callable[[], Page | None], state: HudState) -> None:
        self._page_provider = page_provider
        self._state = state

    @property
    def state(self) -> HudState:
        return self._state

    def state_dict(self) -> dict[str, Any]:
        return self._state.model_dump(mode="json")

    async def set_step(self, index: int, total: int, title: str, phase: StepPhase) -> None:
        self._state.step = HudStep(index=index, total=total, title=title, phase=phase)
        self._state.failure = None
        self._state.final = None
        await self._push()

    async def mark_success(self) -> None:
        if self._state.step is not None:
            self._state.step.status = "passed"
        await self._push()

    async def mark_failure(self, rect: Rect | None, message: str) -> None:
        if self._state.step is not None:
            self._state.step.status = "failed"
        self._state.failure = HudFailure(rect=rect, message=message)
        await self._push()

    async def mark_error(self, message: str) -> None:
        if self._state.step is not None:
            self._state.step.status = "error"
        self._state.failure = HudFailure(rect=None, message=message)
        await self._push()

    async def set_final(self, verdict: Verdict, message: str) -> None:
        self._state.final = HudFinal(verdict=verdict, message=message)
        await self._push()

    async def annotate(self, rect: Rect | None, message: str, tone: AnnotationTone) -> None:
        self._state.annotation = HudAnnotation(rect=rect, message=message, tone=tone)
        await self._push()

    async def clear_annotation(self) -> None:
        self._state.annotation = None
        await self._push()

    async def reapply(self) -> None:
        await self._push()

    async def get_state(self) -> dict[str, Any] | None:
        page = self._page_provider()
        if page is None or page.is_closed():
            return None
        raw: object = await page.evaluate(GET_STATE_SCRIPT)
        return raw if isinstance(raw, dict) else None

    async def _push(self) -> None:
        if not self._state.enabled:
            return
        page = self._page_provider()
        if page is None or page.is_closed():
            return
        with suppress(PlaywrightError):
            await page.evaluate(SET_STATE_SCRIPT, self.state_dict())
