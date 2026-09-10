from __future__ import annotations

import asyncio
from typing import Any

from e2e_verifier.browser.executors.base import LocatorExecutor, StepContext, StepExecutor
from e2e_verifier.domain.enums import ErrorCategory
from e2e_verifier.domain.steps import (
    CheckStep,
    ClickStep,
    DblClickStep,
    FillStep,
    GoBackStep,
    GotoStep,
    HoverStep,
    PressStep,
    ReloadStep,
    ScrollIntoViewStep,
    SelectOptionStep,
    SetViewportStep,
    SleepStep,
    TypeStep,
    UncheckStep,
    UploadFileStep,
    WaitForStep,
)


class GotoExecutor(StepExecutor[GotoStep]):
    step_type = GotoStep
    timeout_category = ErrorCategory.NAVIGATION

    async def run(self, ctx: StepContext, step: GotoStep) -> None:
        url = ctx.rewriter.resolve(step.url)
        ctx.allowlist.ensure(url)
        await ctx.page.goto(url, wait_until=step.wait_until, timeout=ctx.timeout_ms)
        ctx.allowlist.ensure(ctx.page.url)


class ClickExecutor(LocatorExecutor[ClickStep]):
    step_type = ClickStep

    async def run(self, ctx: StepContext, step: ClickStep) -> None:
        await self.locator(ctx, step).click(
            button=step.button,
            click_count=step.click_count,
            force=step.force,
            timeout=ctx.timeout_ms,
        )


class DblClickExecutor(LocatorExecutor[DblClickStep]):
    step_type = DblClickStep

    async def run(self, ctx: StepContext, step: DblClickStep) -> None:
        await self.locator(ctx, step).dblclick(timeout=ctx.timeout_ms)


class FillExecutor(LocatorExecutor[FillStep]):
    step_type = FillStep

    async def run(self, ctx: StepContext, step: FillStep) -> None:
        await self.locator(ctx, step).fill(step.value, timeout=ctx.timeout_ms)


class TypeExecutor(LocatorExecutor[TypeStep]):
    step_type = TypeStep

    async def run(self, ctx: StepContext, step: TypeStep) -> None:
        await self.locator(ctx, step).press_sequentially(
            step.text, delay=step.delay_ms, timeout=ctx.timeout_ms
        )


class PressExecutor(StepExecutor[PressStep]):
    step_type = PressStep

    async def run(self, ctx: StepContext, step: PressStep) -> None:
        if step.target is not None:
            await ctx.resolver.resolve(step.target).press(step.key, timeout=ctx.timeout_ms)
            return
        await ctx.page.keyboard.press(step.key)


class CheckExecutor(LocatorExecutor[CheckStep]):
    step_type = CheckStep

    async def run(self, ctx: StepContext, step: CheckStep) -> None:
        await self.locator(ctx, step).check(timeout=ctx.timeout_ms)


class UncheckExecutor(LocatorExecutor[UncheckStep]):
    step_type = UncheckStep

    async def run(self, ctx: StepContext, step: UncheckStep) -> None:
        await self.locator(ctx, step).uncheck(timeout=ctx.timeout_ms)


class SelectOptionExecutor(LocatorExecutor[SelectOptionStep]):
    step_type = SelectOptionStep

    async def run(self, ctx: StepContext, step: SelectOptionStep) -> None:
        await self.locator(ctx, step).select_option(step.value, timeout=ctx.timeout_ms)


class HoverExecutor(LocatorExecutor[HoverStep]):
    step_type = HoverStep

    async def run(self, ctx: StepContext, step: HoverStep) -> None:
        await self.locator(ctx, step).hover(timeout=ctx.timeout_ms)


class ScrollIntoViewExecutor(LocatorExecutor[ScrollIntoViewStep]):
    step_type = ScrollIntoViewStep

    async def run(self, ctx: StepContext, step: ScrollIntoViewStep) -> None:
        await self.locator(ctx, step).scroll_into_view_if_needed(timeout=ctx.timeout_ms)


class WaitForExecutor(StepExecutor[WaitForStep]):
    step_type = WaitForStep
    timeout_category = ErrorCategory.ELEMENT_NOT_FOUND

    async def run(self, ctx: StepContext, step: WaitForStep) -> None:
        if step.load_state is not None:
            await ctx.page.wait_for_load_state(step.load_state, timeout=ctx.timeout_ms)
            return
        if step.target is not None:
            locator = ctx.resolver.resolve(step.target)
            await locator.wait_for(state=step.state, timeout=ctx.timeout_ms)


class SleepExecutor(StepExecutor[SleepStep]):
    step_type = SleepStep

    async def run(self, ctx: StepContext, step: SleepStep) -> None:
        await asyncio.sleep(step.ms / 1000)


class ReloadExecutor(StepExecutor[ReloadStep]):
    step_type = ReloadStep
    timeout_category = ErrorCategory.NAVIGATION

    async def run(self, ctx: StepContext, step: ReloadStep) -> None:
        await ctx.page.reload(timeout=ctx.timeout_ms)
        ctx.allowlist.ensure(ctx.page.url)


class GoBackExecutor(StepExecutor[GoBackStep]):
    step_type = GoBackStep
    timeout_category = ErrorCategory.NAVIGATION

    async def run(self, ctx: StepContext, step: GoBackStep) -> None:
        await ctx.page.go_back(timeout=ctx.timeout_ms)
        ctx.allowlist.ensure(ctx.page.url)


class SetViewportExecutor(StepExecutor[SetViewportStep]):
    step_type = SetViewportStep

    async def run(self, ctx: StepContext, step: SetViewportStep) -> None:
        await ctx.page.set_viewport_size({"width": step.width, "height": step.height})


class UploadFileExecutor(LocatorExecutor[UploadFileStep]):
    step_type = UploadFileStep

    async def run(self, ctx: StepContext, step: UploadFileStep) -> None:
        path = ctx.fixtures.resolve(step.path)
        await self.locator(ctx, step).set_input_files(path, timeout=ctx.timeout_ms)


ACTION_EXECUTORS: tuple[type[StepExecutor[Any]], ...] = (
    GotoExecutor,
    ClickExecutor,
    DblClickExecutor,
    FillExecutor,
    TypeExecutor,
    PressExecutor,
    CheckExecutor,
    UncheckExecutor,
    SelectOptionExecutor,
    HoverExecutor,
    ScrollIntoViewExecutor,
    WaitForExecutor,
    SleepExecutor,
    ReloadExecutor,
    GoBackExecutor,
    SetViewportExecutor,
    UploadFileExecutor,
)
