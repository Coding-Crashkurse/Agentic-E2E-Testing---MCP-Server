from __future__ import annotations

from e2e_verifier.browser.executors.actions import ACTION_EXECUTORS
from e2e_verifier.browser.executors.assertions import ASSERTION_EXECUTORS
from e2e_verifier.browser.executors.base import FailureClassifier, StepRegistry


class DefaultStepRegistry(StepRegistry):
    def __init__(self) -> None:
        classifier = FailureClassifier()
        executors = [
            executor_type(classifier) for executor_type in (*ACTION_EXECUTORS, *ASSERTION_EXECUTORS)
        ]
        super().__init__(executors)
        self.ensure_complete()
