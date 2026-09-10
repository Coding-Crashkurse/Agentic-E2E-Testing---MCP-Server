from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, Field

from e2e_verifier.domain.common import FrozenModel, StrictModel, TimeoutMs
from e2e_verifier.domain.enums import RunMode, ScreenshotMode
from e2e_verifier.domain.ticket import BrowserName, Environment

type HudLanguage = Literal["de", "en"]
type HudPosition = Literal["top", "bottom"]


class HudOptions(StrictModel):
    enabled: bool = True
    position: HudPosition = "top"
    language: HudLanguage | None = Field(default=None, description="Defaults to E2E_HUD_LANGUAGE")
    show_timer: bool = True
    show_ticket_id: bool = True


class RunOptions(StrictModel):
    mode: RunMode = RunMode.VERIFY
    base_url_override: AnyHttpUrl | None = Field(
        default=None, description="Replaces scheme, host and port of the ticket URL"
    )
    browser: BrowserName | None = None
    headless: bool | None = None
    step_timeout_ms: TimeoutMs | None = None
    run_timeout_s: int | None = Field(default=None, ge=5)
    continue_on_failure: bool = False
    failure_hold_ms: int = Field(default=1500, ge=0, le=10_000)
    post_roll_ms: int = Field(default=1000, ge=0, le=10_000)
    slow_mo_ms: int = Field(default=0, ge=0, le=2000)
    record_har: bool = False
    screenshots: ScreenshotMode = ScreenshotMode.EACH_STEP
    hud: HudOptions = Field(default_factory=HudOptions)
    label: str | None = Field(default=None, max_length=100)


class EffectiveOptions(FrozenModel):
    mode: RunMode
    browser: BrowserName
    headless: bool
    step_timeout_ms: int
    run_timeout_s: int
    continue_on_failure: bool
    failure_hold_ms: int
    post_roll_ms: int
    slow_mo_ms: int
    record_har: bool
    screenshots: ScreenshotMode
    hud_enabled: bool
    hud_position: HudPosition
    hud_language: HudLanguage
    hud_show_timer: bool
    hud_show_ticket_id: bool
    label: str | None
    environment: Environment
