from __future__ import annotations

import asyncio
import shutil
from contextlib import AbstractAsyncContextManager, nullcontext, suppress
from pathlib import Path
from typing import Any, NamedTuple

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    Request,
    Route,
    Video,
    async_playwright,
)
from playwright.async_api import (
    Error as PlaywrightError,
)

from e2e_verifier.application.clock import Clock
from e2e_verifier.application.compiler import ExecutionPlan, PlannedStep
from e2e_verifier.application.fixtures import FixturePaths
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.ports import ClosedSession, ProbeNavigation, SessionObservations
from e2e_verifier.application.store import ArtifactNames
from e2e_verifier.assets.loader import Assets
from e2e_verifier.browser.executors.base import StepContext, StepRegistry
from e2e_verifier.browser.hud import HudController, HudState
from e2e_verifier.browser.locator import LocatorResolver
from e2e_verifier.browser.recorders import Recorders
from e2e_verifier.domain.enums import ErrorCategory
from e2e_verifier.domain.errors import BrowserUnavailableError
from e2e_verifier.domain.result import BrowserInfo, Rect, StepOutcome
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import ExpectDialogStep, Target
from e2e_verifier.domain.ticket import BrowserName

HIGHLIGHT_TIMEOUT_MS = 1500
SCREENSHOT_TIMEOUT_MS = 10_000
ARIA_SNAPSHOT_TIMEOUT_MS = 5000
HUD_BINDING_NAME = "__e2eHudState"


class BrowserKey(NamedTuple):
    name: str
    headless: bool
    slow_mo_ms: int


class BrowserPool:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browsers: dict[BrowserKey, Browser] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def stop(self) -> None:
        for browser in self._browsers.values():
            with suppress(PlaywrightError):
                await browser.close()
        self._browsers.clear()
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def acquire(self, name: BrowserName, headless: bool, slow_mo_ms: int) -> Browser:
        async with self._lock:
            await self.start()
            key = BrowserKey(name, headless, slow_mo_ms)
            browser = self._browsers.get(key)
            if browser is None or not browser.is_connected():
                browser = await self._launch(key)
                self._browsers[key] = browser
            return browser

    async def _launch(self, key: BrowserKey) -> Browser:
        if self._playwright is None:
            raise BrowserUnavailableError("Playwright is not started")
        launchers: dict[str, BrowserType] = {
            "chromium": self._playwright.chromium,
            "firefox": self._playwright.firefox,
            "webkit": self._playwright.webkit,
        }
        return await launchers[key.name].launch(headless=key.headless, slow_mo=key.slow_mo_ms)


class BrowserSessionFactory:
    def __init__(
        self,
        pool: BrowserPool,
        settings: Settings,
        clock: Clock,
        registry: StepRegistry,
        allowlist: HostAllowlist,
    ) -> None:
        self._pool = pool
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._allowlist = allowlist

    def create(
        self, plan: ExecutionPlan, run_dir: Path | None, light: bool = False
    ) -> BrowserSession:
        return BrowserSession(
            pool=self._pool,
            plan=plan,
            run_dir=run_dir,
            light=light,
            settings=self._settings,
            clock=self._clock,
            registry=self._registry,
            allowlist=self._allowlist,
        )


class BrowserSession:
    def __init__(
        self,
        pool: BrowserPool,
        plan: ExecutionPlan,
        run_dir: Path | None,
        light: bool,
        settings: Settings,
        clock: Clock,
        registry: StepRegistry,
        allowlist: HostAllowlist,
    ) -> None:
        options = plan.options
        self._pool = pool
        self._plan = plan
        self._run_dir = run_dir
        self._records = not light and run_dir is not None
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._allowlist = allowlist
        self._rewriter = plan.rewriter()
        self._fixtures = FixturePaths(settings.fixture_dir)
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._resolver: LocatorResolver | None = None
        self._pages: list[Page] = []
        self._tasks: set[asyncio.Task[None]] = set()
        self._origin_ms = 0
        self._violation: str | None = None
        self._browser_version: str | None = None
        self._recorders = Recorders(self.offset_ms, settings.max_log_entries)
        self._hud = HudController(
            lambda: self._page,
            HudState(
                enabled=options.hud_enabled and not light,
                ticket_id=plan.ticket_id,
                mode=plan.mode,
                language=options.hud_language,
                position=options.hud_position,
                show_timer=options.hud_show_timer,
                show_ticket_id=options.hud_show_ticket_id,
            ),
        )

    @property
    def hud(self) -> HudController:
        return self._hud

    @property
    def page(self) -> Page:
        page, _ = self._require()
        return page

    async def open(self) -> None:
        options = self._plan.options
        browser = await self._pool.acquire(options.browser, options.headless, options.slow_mo_ms)
        self._browser_version = browser.version
        context = await browser.new_context(**self._context_options())
        self._context = context
        context.set_default_timeout(options.step_timeout_ms)
        self._origin_ms = self._clock.monotonic_ms()
        self._hud.state.started_at_ms = self._clock.epoch_ms()
        if self._records:
            await context.tracing.start(
                title=f"{self._plan.ticket_id} - {self._plan.title}",
                screenshots=True,
                snapshots=True,
                sources=True,
            )
        await context.route("**/*", self._guard_route)
        if self._hud.state.enabled:
            await context.expose_binding(HUD_BINDING_NAME, self._hud_state_binding)
            await context.add_init_script(script=Assets.hud_script())
        context.on("page", self._on_page)
        self._recorders.attach_context(context)
        page = await context.new_page()
        self._on_page(page)
        self._page = page
        self._resolver = LocatorResolver(page)

    def offset_ms(self) -> int:
        return self._clock.monotonic_ms() - self._origin_ms

    async def trace_group(self, name: str) -> AbstractAsyncContextManager[Any]:
        if not self._records or self._context is None:
            return nullcontext()
        return await self._context.tracing.group(name)

    async def execute(self, planned: PlannedStep, window_start_ms: int) -> StepOutcome:
        page, context = self._require()
        resolver = self._resolver or LocatorResolver(page)
        self._recorders.set_current_step(planned.step.id)
        self._recorders.dialogs.accept_next = self._dialog_policy(planned)
        executor = self._registry.executor_for(planned.step)
        step_context = StepContext(
            page=page,
            context=context,
            resolver=resolver,
            recorders=self._recorders,
            plan=self._plan,
            planned=planned,
            timeout_ms=planned.step.timeout_ms or self._plan.options.step_timeout_ms,
            started_offset_ms=self.offset_ms(),
            window_start_ms=window_start_ms,
            allowlist=self._allowlist,
            rewriter=self._rewriter,
            fixtures=self._fixtures,
            offset=self.offset_ms,
        )
        outcome = await executor.execute(step_context)
        violation = self._violation
        if violation is not None:
            self._violation = None
            return StepOutcome.errored(
                ErrorCategory.HOST_NOT_ALLOWED,
                f"Navigation to {violation} was blocked by the host allowlist",
            )
        return outcome

    async def highlight_rect(self, target: Target) -> Rect | None:
        page, _ = self._require()
        locator = (self._resolver or LocatorResolver(page)).resolve(target)
        if await locator.count() != 1:
            return None
        with suppress(PlaywrightError):
            await locator.scroll_into_view_if_needed(timeout=HIGHLIGHT_TIMEOUT_MS)
        box = await locator.bounding_box(timeout=HIGHLIGHT_TIMEOUT_MS)
        if box is None:
            return None
        return Rect(x=box["x"], y=box["y"], width=box["width"], height=box["height"])

    async def screenshot(self, path: Path, full_page: bool) -> None:
        page, _ = self._require()
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path), full_page=full_page, timeout=SCREENSHOT_TIMEOUT_MS)

    async def screenshot_bytes(self, full_page: bool, jpeg_quality: int | None) -> bytes:
        page, _ = self._require()
        if jpeg_quality is None:
            return await page.screenshot(full_page=full_page, timeout=SCREENSHOT_TIMEOUT_MS)
        return await page.screenshot(
            full_page=full_page,
            type="jpeg",
            quality=jpeg_quality,
            timeout=SCREENSHOT_TIMEOUT_MS,
        )

    async def page_title(self) -> str:
        page, _ = self._require()
        try:
            return await page.title()
        except PlaywrightError:
            return ""

    async def close(self) -> ClosedSession:
        options = self._plan.options
        warnings: list[str] = []
        info = BrowserInfo(
            name=options.browser,
            version=self._browser_version,
            headless=options.headless,
            viewport=options.environment.viewport,
        )
        context = self._context
        if context is None:
            return ClosedSession(browser=info, warnings=warnings)
        trace = await self._stop_tracing(context, warnings)
        videos = [(page, page.video) for page in self._pages]
        try:
            await context.close()
        except PlaywrightError as exc:
            warnings.append(f"closing the browser context failed: {exc}")
        self._context = None
        video, popups = await self._collect_videos(videos, warnings)
        har = self._har_path()
        return ClosedSession(
            video=video,
            popup_videos=popups,
            trace=trace,
            har=har,
            browser=info,
            warnings=warnings,
        )

    def observations(self) -> SessionObservations:
        return self._recorders.snapshot()

    def current_url(self) -> str:
        return self._page.url if self._page is not None else ""

    async def navigate_probe(self, url: str, timeout_ms: int) -> ProbeNavigation:
        page, _ = self._require()
        self._allowlist.ensure(url)
        started = self.offset_ms()
        response = await page.goto(url, wait_until="load", timeout=timeout_ms)
        load_time = self.offset_ms() - started
        if self._violation is not None:
            blocked = self._violation
            self._violation = None
            raise BrowserUnavailableError(f"navigation to {blocked} was blocked by the allowlist")
        return ProbeNavigation(
            status=response.status if response is not None else None,
            final_url=page.url,
            title=await page.title(),
            load_time_ms=load_time,
        )

    async def aria_snapshot(self) -> str:
        page, _ = self._require()
        return await page.locator("body").aria_snapshot(timeout=ARIA_SNAPSHOT_TIMEOUT_MS)

    async def discover(self, query: str | None, max_results: int) -> list[dict[str, Any]]:
        page, _ = self._require()
        raw: object = await page.evaluate(Assets.discover_script(), [query, max_results])
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    def _require(self) -> tuple[Page, BrowserContext]:
        if self._page is None or self._context is None:
            raise BrowserUnavailableError("browser session is not open")
        return self._page, self._context

    def _context_options(self) -> dict[str, Any]:
        options = self._plan.options
        environment = options.environment
        viewport = {"width": environment.viewport.width, "height": environment.viewport.height}
        kwargs: dict[str, Any] = {"viewport": viewport}
        if self._records and self._run_dir is not None:
            kwargs["record_video_dir"] = str(self._run_dir / ArtifactNames.VIDEO_RAW)
            kwargs["record_video_size"] = viewport
            if options.record_har:
                kwargs["record_har_path"] = str(self._run_dir / ArtifactNames.HAR)
        if environment.locale:
            kwargs["locale"] = environment.locale
        if environment.timezone:
            kwargs["timezone_id"] = environment.timezone
        if environment.color_scheme:
            kwargs["color_scheme"] = environment.color_scheme
        if environment.storage_state_path:
            kwargs["storage_state"] = str(self._fixtures.resolve(environment.storage_state_path))
        return kwargs

    async def _guard_route(self, route: Route, request: Request) -> None:
        if (
            request.is_navigation_request()
            and self._is_main_frame(request)
            and not self._allowlist.allows(request.url)
        ):
            self._violation = request.url
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    @staticmethod
    def _is_main_frame(request: Request) -> bool:
        try:
            return request.frame.parent_frame is None
        except PlaywrightError:
            return True

    def _hud_state_binding(self, source: Any) -> dict[str, Any]:
        return self._hud.state_dict()

    def _on_page(self, page: Page) -> None:
        if any(page is known for known in self._pages):
            return
        self._pages.append(page)
        self._recorders.attach_page(page)
        page.on("load", self._on_load)

    def _on_load(self, page: Page) -> None:
        if page is not self._page:
            return
        task = asyncio.create_task(self._hud.reapply())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _dialog_policy(self, planned: PlannedStep) -> bool:
        following = [step for step in self._plan.steps if step.index == planned.index + 1]
        if following and isinstance(following[0].step, ExpectDialogStep):
            return following[0].step.accept
        return True

    async def _stop_tracing(self, context: BrowserContext, warnings: list[str]) -> Path | None:
        if not self._records or self._run_dir is None:
            return None
        target = self._run_dir / ArtifactNames.TRACE
        try:
            await context.tracing.stop(path=str(target))
        except PlaywrightError as exc:
            warnings.append(f"stopping the trace failed: {exc}")
            return None
        return target if target.is_file() else None

    async def _collect_videos(
        self, videos: list[tuple[Page, Video | None]], warnings: list[str]
    ) -> tuple[Path | None, list[Path]]:
        if not self._records or self._run_dir is None:
            return None, []
        main: Path | None = None
        popups: list[Path] = []
        for page, video in videos:
            if video is None:
                continue
            is_main = page is self._page
            name = ArtifactNames.VIDEO if is_main else f"video_popup_{len(popups) + 1}.webm"
            target = self._run_dir / name
            if not await self._save_video(video, target, warnings):
                continue
            if is_main:
                main = target
            else:
                popups.append(target)
        shutil.rmtree(self._run_dir / ArtifactNames.VIDEO_RAW, ignore_errors=True)
        return main, popups

    @staticmethod
    async def _save_video(video: Video, target: Path, warnings: list[str]) -> bool:
        try:
            await video.save_as(str(target))
        except PlaywrightError:
            try:
                source = await video.path()
                shutil.move(str(source), str(target))
            except (PlaywrightError, OSError) as exc:
                warnings.append(f"saving the video failed: {exc}")
                return False
        return target.is_file()

    def _har_path(self) -> Path | None:
        if not self._records or self._run_dir is None or not self._plan.options.record_har:
            return None
        path = self._run_dir / ArtifactNames.HAR
        return path if path.is_file() else None
