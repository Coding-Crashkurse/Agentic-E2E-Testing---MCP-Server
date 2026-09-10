from __future__ import annotations

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from e2e_verifier.browser.executors.base import FailureClassifier
from e2e_verifier.domain.enums import ErrorCategory, StepStatus

ASSERTION_MESSAGE = (
    "Locator expected to be visible\n"
    "Actual value: None\n"
    "Call log:\n"
    '  - Expect "to_be_visible" with timeout 3000ms\n'
    '  - waiting for get_by_test_id("summary-discount")\n'
    "Aria snapshot:\n"
    "- banner:\n"
    '  - link "ShopDesk"\n'
    "- main:\n"
    '  - heading "Your cart" [level=1]\n'
)

STRICT_MESSAGE = (
    'Locator.click: Error: strict mode violation: get_by_role("button") resolved to 2 elements:\n'
    '    1) <button type="button">Save</button> aka get_by_role("button", name="Save")\n'
    '    2) <button type="button">Delete</button> aka get_by_role("button", name="Delete")\n'
)


def test_assertion_message_drops_aria_snapshot_and_keeps_call_log() -> None:
    outcome = FailureClassifier().classify(
        AssertionError(ASSERTION_MESSAGE),
        "get_by_test_id('summary-discount')",
        ErrorCategory.TIMEOUT,
    )
    assert outcome.status is StepStatus.FAILED
    assert outcome.error is not None
    assert outcome.error.category is ErrorCategory.ASSERTION
    assert "Aria snapshot" not in outcome.error.message
    assert "ShopDesk" not in outcome.error.message
    assert "waiting for get_by_test_id" in outcome.error.message
    assert outcome.error.locator == "get_by_test_id('summary-discount')"


def test_strict_mode_violation_becomes_error_with_candidates() -> None:
    outcome = FailureClassifier().classify(
        PlaywrightError(STRICT_MESSAGE), "get_by_role('button')", ErrorCategory.ELEMENT_NOT_FOUND
    )
    assert outcome.status is StepStatus.ERROR
    assert outcome.error is not None
    assert outcome.error.category is ErrorCategory.AMBIGUOUS_TARGET
    assert len(outcome.error.candidates) == 2
    assert outcome.error.candidates[0].startswith("<button")


def test_timeout_uses_executor_category() -> None:
    outcome = FailureClassifier().classify(
        PlaywrightTimeoutError("Timeout 4000ms exceeded."), None, ErrorCategory.ELEMENT_NOT_FOUND
    )
    assert outcome.status is StepStatus.FAILED
    assert outcome.error is not None
    assert outcome.error.category is ErrorCategory.ELEMENT_NOT_FOUND


def test_navigation_and_browser_errors() -> None:
    classifier = FailureClassifier()
    navigation = classifier.classify(
        PlaywrightError("Page.goto: net::ERR_CONNECTION_REFUSED at http://x/"),
        None,
        ErrorCategory.TIMEOUT,
    )
    assert navigation.error is not None
    assert navigation.error.category is ErrorCategory.NAVIGATION
    crashed = classifier.classify(
        PlaywrightError("Target page, context or browser has been closed"),
        None,
        ErrorCategory.TIMEOUT,
    )
    assert crashed.error is not None
    assert crashed.error.category is ErrorCategory.BROWSER
    unknown = classifier.classify(RuntimeError("boom"), None, ErrorCategory.TIMEOUT)
    assert unknown.status is StepStatus.ERROR
    assert unknown.error is not None
    assert unknown.error.category is ErrorCategory.INTERNAL
    assert unknown.error.message.startswith("RuntimeError: boom")


def test_long_messages_are_truncated() -> None:
    message = "x" * 2000
    cleaned = FailureClassifier.clean(message)
    assert len(cleaned) == 700
    assert cleaned.endswith("...")
