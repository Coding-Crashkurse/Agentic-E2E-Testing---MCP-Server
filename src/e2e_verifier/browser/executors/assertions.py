from __future__ import annotations

import asyncio
import re
from fnmatch import fnmatchcase
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import expect

from e2e_verifier.application.urls import UrlPattern
from e2e_verifier.browser.executors.base import LocatorExecutor, StepContext, StepExecutor
from e2e_verifier.domain.result import DialogEntry, NetworkEntry
from e2e_verifier.domain.steps import (
    ExpectAttributeStep,
    ExpectCheckedStep,
    ExpectConsoleContainsStep,
    ExpectCountStep,
    ExpectDialogStep,
    ExpectDisabledStep,
    ExpectDownloadStep,
    ExpectEnabledStep,
    ExpectHiddenStep,
    ExpectNoConsoleErrorsStep,
    ExpectNoRequestStep,
    ExpectRequestStep,
    ExpectStorageStep,
    ExpectTextStep,
    ExpectTitleStep,
    ExpectUrlStep,
    ExpectValueStep,
    ExpectVisibleStep,
)

ANY_VALUE = re.compile(r"[\s\S]*")
MAX_LISTED_ERRORS = 3


class ExpectVisibleExecutor(LocatorExecutor[ExpectVisibleStep]):
    step_type = ExpectVisibleStep

    async def run(self, ctx: StepContext, step: ExpectVisibleStep) -> None:
        await expect(self.locator(ctx, step)).to_be_visible(timeout=ctx.timeout_ms)


class ExpectHiddenExecutor(LocatorExecutor[ExpectHiddenStep]):
    step_type = ExpectHiddenStep

    async def run(self, ctx: StepContext, step: ExpectHiddenStep) -> None:
        await expect(self.locator(ctx, step)).to_be_hidden(timeout=ctx.timeout_ms)


class ExpectTextExecutor(LocatorExecutor[ExpectTextStep]):
    step_type = ExpectTextStep

    async def run(self, ctx: StepContext, step: ExpectTextStep) -> None:
        locator = self.locator(ctx, step)
        if step.exact:
            await expect(locator).to_have_text(step.text, timeout=ctx.timeout_ms)
            return
        await expect(locator).to_contain_text(step.text, timeout=ctx.timeout_ms)


class ExpectValueExecutor(LocatorExecutor[ExpectValueStep]):
    step_type = ExpectValueStep

    async def run(self, ctx: StepContext, step: ExpectValueStep) -> None:
        await expect(self.locator(ctx, step)).to_have_value(step.value, timeout=ctx.timeout_ms)


class ExpectAttributeExecutor(LocatorExecutor[ExpectAttributeStep]):
    step_type = ExpectAttributeStep

    async def run(self, ctx: StepContext, step: ExpectAttributeStep) -> None:
        value: str | re.Pattern[str] = ANY_VALUE if step.value is None else step.value
        await expect(self.locator(ctx, step)).to_have_attribute(
            step.name, value, timeout=ctx.timeout_ms
        )


class ExpectEnabledExecutor(LocatorExecutor[ExpectEnabledStep]):
    step_type = ExpectEnabledStep

    async def run(self, ctx: StepContext, step: ExpectEnabledStep) -> None:
        await expect(self.locator(ctx, step)).to_be_enabled(timeout=ctx.timeout_ms)


class ExpectDisabledExecutor(LocatorExecutor[ExpectDisabledStep]):
    step_type = ExpectDisabledStep

    async def run(self, ctx: StepContext, step: ExpectDisabledStep) -> None:
        await expect(self.locator(ctx, step)).to_be_disabled(timeout=ctx.timeout_ms)


class ExpectCheckedExecutor(LocatorExecutor[ExpectCheckedStep]):
    step_type = ExpectCheckedStep

    async def run(self, ctx: StepContext, step: ExpectCheckedStep) -> None:
        await expect(self.locator(ctx, step)).to_be_checked(
            checked=step.checked, timeout=ctx.timeout_ms
        )


class ExpectCountExecutor(LocatorExecutor[ExpectCountStep]):
    step_type = ExpectCountStep

    async def run(self, ctx: StepContext, step: ExpectCountStep) -> None:
        await expect(self.locator(ctx, step)).to_have_count(step.count, timeout=ctx.timeout_ms)


class ExpectUrlExecutor(StepExecutor[ExpectUrlStep]):
    step_type = ExpectUrlStep

    async def run(self, ctx: StepContext, step: ExpectUrlStep) -> None:
        await expect(ctx.page).to_have_url(UrlPattern(step.pattern).regex, timeout=ctx.timeout_ms)


class ExpectTitleExecutor(StepExecutor[ExpectTitleStep]):
    step_type = ExpectTitleStep

    async def run(self, ctx: StepContext, step: ExpectTitleStep) -> None:
        pattern = re.compile(re.escape(step.text))
        await expect(ctx.page).to_have_title(pattern, timeout=ctx.timeout_ms)


class ExpectRequestExecutor(StepExecutor[ExpectRequestStep]):
    step_type = ExpectRequestStep

    async def run(self, ctx: StepContext, step: ExpectRequestStep) -> None:
        pattern = UrlPattern(step.url_pattern)
        recorder = ctx.recorders.network
        since = ctx.window_start_ms
        if step.status is None and step.body_contains is None:
            found = await recorder.wait_for(
                lambda: self._first(recorder.requests_since(since, step.method, pattern)),
                ctx.timeout_ms,
            )
            if found is None:
                raise AssertionError(self._message(ctx, step, since))
            return
        matched = await recorder.wait_for(
            lambda: self._first(recorder.responses_since(since, step.method, pattern)),
            ctx.timeout_ms,
        )
        if matched is None:
            raise AssertionError(self._message(ctx, step, since))
        await self._check_response(ctx, step, matched, since)

    async def _check_response(
        self,
        ctx: StepContext,
        step: ExpectRequestStep,
        matched: tuple[NetworkEntry, object],
        since: int,
    ) -> None:
        pattern = UrlPattern(step.url_pattern)
        recorder = ctx.recorders.network
        deadline = ctx.offset() + ctx.timeout_ms
        while True:
            for entry, response in recorder.responses_since(since, step.method, pattern):
                if await self._satisfies(step, entry, response):
                    return
            remaining = deadline - ctx.offset()
            if remaining <= 0:
                raise AssertionError(self._message(ctx, step, since, matched[0]))
            await recorder.wait_for(lambda: None, min(remaining, 250))

    @staticmethod
    async def _satisfies(step: ExpectRequestStep, entry: NetworkEntry, response: object) -> bool:
        if step.status is not None and entry.status != step.status:
            return False
        if step.body_contains is None:
            return True
        text_method = getattr(response, "text", None)
        if text_method is None:
            return False
        try:
            body = await text_method()
        except PlaywrightError:
            return False
        return step.body_contains in body

    @staticmethod
    def _first[T](items: list[T]) -> T | None:
        return items[0] if items else None

    @staticmethod
    def _message(
        ctx: StepContext, step: ExpectRequestStep, since: int, seen: NetworkEntry | None = None
    ) -> str:
        total = len(ctx.recorders.network.requests_since(since, "ANY", UrlPattern("**")))
        detail = ""
        if seen is not None:
            detail = f"; closest match {seen.method} {seen.url} -> status {seen.status}"
        return (
            f"No request {step.method} {step.url_pattern}"
            f"{' with status ' + str(step.status) if step.status is not None else ''}"
            f"{' containing ' + repr(step.body_contains) if step.body_contains else ''}"
            f" within {ctx.timeout_ms} ms ({total} requests observed since the last action{detail})"
        )


class ExpectNoRequestExecutor(StepExecutor[ExpectNoRequestStep]):
    step_type = ExpectNoRequestStep

    async def run(self, ctx: StepContext, step: ExpectNoRequestStep) -> None:
        await asyncio.sleep(step.within_ms / 1000)
        pattern = UrlPattern(step.url_pattern)
        seen = ctx.recorders.network.requests_since(ctx.window_start_ms, step.method, pattern)
        if seen:
            raise AssertionError(
                f"Unexpected request {seen[0].method} {seen[0].url} "
                f"({len(seen)} matching {step.method} {step.url_pattern})"
            )


class ExpectNoConsoleErrorsExecutor(StepExecutor[ExpectNoConsoleErrorsStep]):
    step_type = ExpectNoConsoleErrorsStep

    async def run(self, ctx: StepContext, step: ExpectNoConsoleErrorsStep) -> None:
        console = ctx.recorders.console
        errors = console.errors_since(console.checkpoint_ms, step.ignore_patterns)
        console.checkpoint_ms = ctx.offset()
        if errors:
            listed = "; ".join(entry.text.splitlines()[0] for entry in errors[:MAX_LISTED_ERRORS])
            raise AssertionError(f"{len(errors)} console/page errors: {listed}")


class ExpectConsoleContainsExecutor(StepExecutor[ExpectConsoleContainsStep]):
    step_type = ExpectConsoleContainsStep

    async def run(self, ctx: StepContext, step: ExpectConsoleContainsStep) -> None:
        if not ctx.recorders.console.matching(step.level, step.pattern):
            level = step.level or "any"
            raise AssertionError(f"No console message (level {level}) matching {step.pattern!r}")


class ExpectDialogExecutor(StepExecutor[ExpectDialogStep]):
    step_type = ExpectDialogStep

    async def run(self, ctx: StepContext, step: ExpectDialogStep) -> None:
        dialogs = ctx.recorders.dialogs.since(ctx.window_start_ms)
        matching = [dialog for dialog in dialogs if self._matches(step, dialog)]
        if not matching:
            raise AssertionError(
                f"No {step.dialog_type} dialog since the last action ({len(dialogs)} dialogs seen)"
            )

    @staticmethod
    def _matches(step: ExpectDialogStep, dialog: DialogEntry) -> bool:
        if dialog.dialog_type != step.dialog_type:
            return False
        return step.message_contains is None or step.message_contains in dialog.message


class ExpectStorageExecutor(StepExecutor[ExpectStorageStep]):
    step_type = ExpectStorageStep

    async def run(self, ctx: StepContext, step: ExpectStorageStep) -> None:
        script = (
            "([kind, key]) => (kind === 'local' ? window.localStorage : window.sessionStorage)"
            ".getItem(key)"
        )
        raw: object = await ctx.page.evaluate(script, [step.kind_of_storage, step.key])
        if raw is None:
            raise AssertionError(f"{step.kind_of_storage}Storage has no key {step.key!r}")
        if step.value is not None and raw != step.value:
            raise AssertionError(
                f"{step.kind_of_storage}Storage[{step.key!r}] is {raw!r}, expected {step.value!r}"
            )


class ExpectDownloadExecutor(StepExecutor[ExpectDownloadStep]):
    step_type = ExpectDownloadStep

    async def run(self, ctx: StepContext, step: ExpectDownloadStep) -> None:
        downloads = ctx.recorders.downloads.since(ctx.window_start_ms)
        if step.filename_pattern is not None:
            downloads = [
                item
                for item in downloads
                if fnmatchcase(item.suggested_filename, step.filename_pattern)
            ]
        if not downloads:
            raise AssertionError("No download was triggered since the last action")


ASSERTION_EXECUTORS: tuple[type[StepExecutor[Any]], ...] = (
    ExpectVisibleExecutor,
    ExpectHiddenExecutor,
    ExpectTextExecutor,
    ExpectValueExecutor,
    ExpectAttributeExecutor,
    ExpectEnabledExecutor,
    ExpectDisabledExecutor,
    ExpectCheckedExecutor,
    ExpectCountExecutor,
    ExpectUrlExecutor,
    ExpectTitleExecutor,
    ExpectRequestExecutor,
    ExpectNoRequestExecutor,
    ExpectNoConsoleErrorsExecutor,
    ExpectConsoleContainsExecutor,
    ExpectDialogExecutor,
    ExpectStorageExecutor,
    ExpectDownloadExecutor,
)
