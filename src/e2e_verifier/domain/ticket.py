from __future__ import annotations

from typing import Literal, Self

from pydantic import AnyHttpUrl, Field, model_validator

from e2e_verifier.domain.common import Identifier, StrictModel
from e2e_verifier.domain.steps import Step, StepBase

type BrowserName = Literal["chromium", "firefox", "webkit"]
type ColorScheme = Literal["light", "dark", "no-preference"]

MAX_TITLE_LENGTH = 200


class Viewport(StrictModel):
    width: int = Field(default=1280, ge=320, le=4000)
    height: int = Field(default=720, ge=240, le=4000)


class Environment(StrictModel):
    viewport: Viewport = Field(default_factory=Viewport)
    browser: BrowserName | None = None
    locale: str | None = None
    timezone: str | None = None
    color_scheme: ColorScheme | None = None
    storage_state_path: str | None = Field(
        default=None, description="Playwright storage state file relative to E2E_FIXTURE_DIR"
    )


class AcceptanceCriterion(StrictModel):
    id: Identifier
    description: str = Field(min_length=1, max_length=500)
    step_ids: list[Identifier] = Field(min_length=1, description="Assertion steps proving it")


class ScenarioBase(StrictModel):
    id: Identifier
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    url: AnyHttpUrl = Field(description="Base URL of the site under test")
    description: str | None = None
    environment: Environment = Field(default_factory=Environment)
    preconditions: list[Step] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_step_ids(self) -> Self:
        seen: set[str] = set()
        for step in self.all_steps():
            if step.id in seen:
                raise ValueError(f"Duplicate step id: {step.id}")
            seen.add(step.id)
        return self

    def all_steps(self) -> list[StepBase]:
        return [*self.preconditions, *self.steps]

    def step_by_id(self, step_id: str) -> StepBase | None:
        return next((step for step in self.all_steps() if step.id == step_id), None)

    def main_step_ids(self) -> set[str]:
        return {step.id for step in self.steps}


class Scenario(ScenarioBase):
    pass


class BugTicket(ScenarioBase):
    expected: str = Field(min_length=1)
    actual: str | None = None
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)

    @model_validator(mode="after")
    def _criteria_reference_assertions(self) -> Self:
        ids = self.main_step_ids()
        seen: set[str] = set()
        for criterion in self.acceptance_criteria:
            if criterion.id in seen:
                raise ValueError(f"Duplicate acceptance criterion id: {criterion.id}")
            seen.add(criterion.id)
            for step_id in criterion.step_ids:
                if step_id not in ids:
                    raise ValueError(
                        f"Criterion {criterion.id} references unknown step {step_id!r}"
                    )
                step = self.step_by_id(step_id)
                if step is not None and not step.is_assertion:
                    raise ValueError(
                        f"Criterion {criterion.id} references action step {step_id!r}; "
                        "only assertion steps may prove a criterion"
                    )
        return self
