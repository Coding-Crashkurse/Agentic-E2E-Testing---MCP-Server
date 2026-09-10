from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, ClassVar, cast

from playwright.async_api import BrowserContext, Page
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from e2e_verifier.application.compiler import ExecutionPlan, PlannedStep
from e2e_verifier.application.fixtures import FixturePaths
from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.urls import UrlRewriter
from e2e_verifier.browser.locator import LocatorResolver
from e2e_verifier.browser.recorders import Recorders
from e2e_verifier.domain.enums import ErrorCategory
from e2e_verifier.domain.errors import FixturePathError, HostNotAllowedError
from e2e_verifier.domain.result import StepOutcome
from e2e_verifier.domain.steps import STEP_TYPES, StepBase, TargetStep, action_name

MAX_MESSAGE_LENGTH = 700
ARIA_SNAPSHOT_MARKER = "Aria snapshot:"
CANDIDATE_LINE = re.compile(r"^\s*\d+\)\s*(.+?)\s*$")


@dataclass(slots=True)
class StepContext:
    page: Page
    context: BrowserContext
    resolver: LocatorResolver
    recorders: Recorders
    plan: ExecutionPlan
    planned: PlannedStep
    timeout_ms: int
    started_offset_ms: int
    window_start_ms: int
    allowlist: HostAllowlist
    rewriter: UrlRewriter
    fixtures: FixturePaths
    offset: Callable[[], int]


class FailureClassifier:
    def classify(
        self, exc: BaseException, locator: str | None, timeout_category: ErrorCategory
    ) -> StepOutcome:
        message = self.clean(str(exc))
        if isinstance(exc, AssertionError):
            return StepOutcome.failed(ErrorCategory.ASSERTION, message, locator)
        if isinstance(exc, HostNotAllowedError):
            return StepOutcome.errored(ErrorCategory.HOST_NOT_ALLOWED, message)
        if isinstance(exc, FixturePathError):
            return StepOutcome.errored(ErrorCategory.INPUT, message)
        if isinstance(exc, PlaywrightTimeoutError):
            return StepOutcome.failed(timeout_category, message, locator)
        if isinstance(exc, PlaywrightError):
            return self._classify_playwright(exc, message, locator)
        return StepOutcome.errored(ErrorCategory.INTERNAL, f"{type(exc).__name__}: {message}")

    def _classify_playwright(
        self, exc: PlaywrightError, message: str, locator: str | None
    ) -> StepOutcome:
        raw = str(exc)
        if "strict mode violation" in raw:
            outcome = StepOutcome.errored(ErrorCategory.AMBIGUOUS_TARGET, message, locator)
            if outcome.error is not None:
                outcome.error.candidates = self.candidates(raw)
            return outcome
        if "net::ERR" in raw or "NS_ERROR" in raw or "Navigation failed" in raw:
            return StepOutcome.errored(ErrorCategory.NAVIGATION, message)
        if "has been closed" in raw or "crashed" in raw or "Target closed" in raw:
            return StepOutcome.errored(ErrorCategory.BROWSER, message)
        return StepOutcome.errored(ErrorCategory.INPUT, message, locator)

    @staticmethod
    def clean(message: str) -> str:
        head = message.split(ARIA_SNAPSHOT_MARKER, 1)[0]
        collapsed = re.sub(r"[ \t]+", " ", head).strip()
        collapsed = re.sub(r"\n{2,}", "\n", collapsed)
        if len(collapsed) > MAX_MESSAGE_LENGTH:
            return collapsed[: MAX_MESSAGE_LENGTH - 3] + "..."
        return collapsed

    @staticmethod
    def candidates(message: str) -> list[str]:
        found: list[str] = []
        for line in message.splitlines():
            match = CANDIDATE_LINE.match(line)
            if match:
                found.append(match.group(1))
        return found


class StepExecutor[S: StepBase](ABC):
    step_type: ClassVar[type[StepBase]]
    timeout_category: ClassVar[ErrorCategory] = ErrorCategory.TIMEOUT

    def __init__(self, classifier: FailureClassifier | None = None) -> None:
        self._classifier = classifier or FailureClassifier()

    @property
    def action(self) -> str:
        return action_name(self.step_type)

    @abstractmethod
    async def run(self, ctx: StepContext, step: S) -> None: ...

    def locator_description(self, ctx: StepContext, step: S) -> str | None:
        target = step.target_or_none
        return ctx.resolver.describe(target) if target is not None else None

    async def execute(self, ctx: StepContext) -> StepOutcome:
        step = cast("S", ctx.planned.step)
        try:
            await self.run(ctx, step)
        except Exception as exc:
            return self._classifier.classify(
                exc, self.locator_description(ctx, step), self.timeout_category
            )
        return StepOutcome.passed()


class LocatorExecutor[S: TargetStep](StepExecutor[S]):
    timeout_category = ErrorCategory.ELEMENT_NOT_FOUND

    @staticmethod
    def locator(ctx: StepContext, step: S) -> Any:
        return ctx.resolver.resolve(step.target)


class StepRegistry:
    def __init__(self, executors: Iterable[StepExecutor[Any]]) -> None:
        self._by_action: dict[str, StepExecutor[Any]] = {}
        for executor in executors:
            if executor.action in self._by_action:
                raise ValueError(f"duplicate executor for action {executor.action!r}")
            self._by_action[executor.action] = executor

    def executor_for(self, step: StepBase) -> StepExecutor[Any]:
        return self._by_action[action_name(type(step))]

    def ensure_complete(self) -> None:
        missing = {action_name(step_type) for step_type in STEP_TYPES} - set(self._by_action)
        if missing:
            raise ValueError(f"missing executors for actions: {sorted(missing)}")

    @property
    def actions(self) -> list[str]:
        return sorted(self._by_action)
