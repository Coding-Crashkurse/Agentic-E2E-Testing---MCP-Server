from __future__ import annotations

from pydantic import AnyHttpUrl

from e2e_verifier.application.compiler import IMPLICIT_GOTO_ID, PlanCompiler
from e2e_verifier.domain.enums import RunKind, RunMode, StepPhase
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import GotoStep
from e2e_verifier.domain.ticket import BugTicket, Scenario


def make_settings() -> Settings:
    return Settings(_env_file=None, default_step_timeout_ms=7000, hud_language="de")


def make_ticket(**overrides: object) -> BugTicket:
    payload: dict[str, object] = {
        "id": "T-1",
        "title": "t",
        "url": "http://localhost:5173/settings",
        "steps": [
            {"id": "s1", "action": "click", "target": {"test_id": "save"}},
            {"id": "s2", "action": "expect_visible", "target": {"test_id": "toast"}},
        ],
        "expected": "x",
        "acceptance_criteria": [{"id": "AC1", "description": "d", "step_ids": ["s2"]}],
    }
    payload.update(overrides)
    return BugTicket.model_validate(payload)


def test_implicit_goto_is_prepended_as_precondition() -> None:
    plan = PlanCompiler(make_settings()).compile(make_ticket(), None)
    first = plan.steps[0]
    assert isinstance(first.step, GotoStep)
    assert first.step.id == IMPLICIT_GOTO_ID
    assert first.phase is StepPhase.PRECONDITIONS
    assert first.step.url == "http://localhost:5173/settings"
    assert [planned.index for planned in plan.steps] == [1, 2, 3]


def test_explicit_goto_first_skips_implicit_goto() -> None:
    ticket = make_ticket(
        steps=[
            {"id": "g", "action": "goto", "url": "/other"},
            {"id": "s2", "action": "expect_visible", "target": {"test_id": "toast"}},
        ]
    )
    plan = PlanCompiler(make_settings()).compile(ticket, None)
    assert plan.steps[0].step.id == "g"
    assert plan.steps[0].phase is StepPhase.STEPS


def test_preconditions_get_setup_phase_and_trace_names() -> None:
    ticket = make_ticket(preconditions=[{"id": "p1", "action": "goto", "url": "/login"}])
    plan = PlanCompiler(make_settings()).compile(ticket, None)
    assert plan.steps[0].phase is StepPhase.PRECONDITIONS
    assert plan.steps[0].trace_group.startswith("Setup 1/3")
    assert plan.steps[1].trace_group.startswith("Step 2/3")


def test_options_resolve_from_settings_and_ticket_environment() -> None:
    ticket = make_ticket(
        environment={"browser": "firefox", "viewport": {"width": 800, "height": 600}}
    )
    plan = PlanCompiler(make_settings()).compile(ticket, RunOptions(mode=RunMode.REPRODUCE))
    assert plan.options.browser == "firefox"
    assert plan.options.step_timeout_ms == 7000
    assert plan.options.hud_language == "de"
    assert plan.options.environment.viewport.width == 800
    assert plan.mode is RunMode.REPRODUCE


def test_run_timeout_is_capped_by_settings() -> None:
    settings = Settings(_env_file=None, max_run_timeout_s=30)
    plan = PlanCompiler(settings).compile(make_ticket(), RunOptions(run_timeout_s=500))
    assert plan.options.run_timeout_s == 30


def test_base_url_override_rewrites_target_and_relative_goto() -> None:
    ticket = make_ticket(
        steps=[
            {"id": "g", "action": "goto", "url": "/settings?x=1"},
            {"id": "s2", "action": "expect_visible", "target": {"test_id": "toast"}},
        ]
    )
    options = RunOptions(base_url_override=AnyHttpUrl("http://127.0.0.1:4173"))
    plan = PlanCompiler(make_settings()).compile(ticket, options)
    assert plan.target_url == "http://127.0.0.1:4173/settings"
    assert plan.rewriter().resolve("/settings?x=1") == "http://127.0.0.1:4173/settings?x=1"
    assert plan.rewriter().resolve("http://localhost:5173/cart") == "http://127.0.0.1:4173/cart"
    assert plan.rewriter().resolve("http://other.test/") == "http://other.test/"


def test_scenario_gets_implicit_criteria_per_assertion() -> None:
    scenario = Scenario.model_validate(
        {
            "id": "sc",
            "title": "sc",
            "url": "http://localhost/",
            "steps": [
                {"id": "a", "action": "click", "target": {"css": "button"}},
                {"id": "b", "action": "expect_url", "pattern": "**/done"},
                {"id": "c", "action": "expect_title", "text": "Done"},
            ],
        }
    )
    plan = PlanCompiler(make_settings()).compile(scenario, RunOptions(mode=RunMode.REPRODUCE))
    assert plan.kind is RunKind.SCENARIO
    assert plan.mode is RunMode.VERIFY
    assert [criterion.id for criterion in plan.criteria] == ["b", "c"]


def test_secrets_are_masked_in_plan_source() -> None:
    ticket = make_ticket(
        steps=[
            {
                "id": "f",
                "action": "fill",
                "target": {"label": "pw"},
                "value": "hunter2",
                "secret": True,
            },
            {"id": "s2", "action": "expect_visible", "target": {"test_id": "toast"}},
        ]
    )
    plan = PlanCompiler(make_settings()).compile(ticket, None)
    assert plan.secrets == ["hunter2"]
    assert "hunter2" not in plan.source.model_dump_json()
