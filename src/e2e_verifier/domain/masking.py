from __future__ import annotations

from e2e_verifier.domain.steps import MASKED_VALUE, FillStep, StepBase
from e2e_verifier.domain.ticket import BugTicket, Scenario


class SecretMasker:
    def secret_values(self, source: BugTicket | Scenario) -> list[str]:
        return [
            step.value
            for step in source.all_steps()
            if isinstance(step, FillStep) and step.secret and step.value
        ]

    def mask_source(self, source: BugTicket | Scenario) -> BugTicket | Scenario:
        return source.model_copy(
            update={
                "preconditions": [self._mask_step(step) for step in source.preconditions],
                "steps": [self._mask_step(step) for step in source.steps],
            }
        )

    def mask_text(self, text: str, secrets: list[str]) -> str:
        masked = text
        for secret in sorted(secrets, key=len, reverse=True):
            masked = masked.replace(secret, MASKED_VALUE)
        return masked

    def _mask_step(self, step: StepBase) -> StepBase:
        if isinstance(step, FillStep) and step.secret:
            return step.model_copy(update={"value": MASKED_VALUE})
        return step
