from __future__ import annotations

import pytest
from pydantic import ValidationError

from e2e_verifier.domain.steps import (
    STEP_TYPES,
    ClickStep,
    ExpectDialogStep,
    FillStep,
    RoleTarget,
    Target,
    WaitForStep,
    action_name,
)
from e2e_verifier.domain.ticket import BugTicket, Scenario


def ticket_payload() -> dict[str, object]:
    return {
        "id": "WEB-142",
        "title": "Save button does nothing",
        "url": "http://localhost:5173/settings",
        "steps": [
            {"id": "s1", "action": "fill", "target": {"label": "Name"}, "value": "Anna"},
            {"id": "s2", "action": "click", "target": {"role": {"role": "button", "name": "Save"}}},
            {"id": "s3", "action": "expect_visible", "target": {"role": {"role": "status"}}},
        ],
        "expected": "Toast appears",
        "acceptance_criteria": [{"id": "AC1", "description": "toast", "step_ids": ["s3"]}],
    }


def test_ticket_roundtrip_keeps_step_types() -> None:
    ticket = BugTicket.model_validate(ticket_payload())
    assert [type(step) for step in ticket.steps][:2] == [FillStep, ClickStep]
    restored = BugTicket.model_validate_json(ticket.model_dump_json(by_alias=True))
    assert restored == ticket


def test_extra_fields_are_rejected() -> None:
    payload = ticket_payload()
    payload["unexpected"] = 1
    with pytest.raises(ValidationError, match="unexpected"):
        BugTicket.model_validate(payload)


def test_unknown_action_is_rejected() -> None:
    payload = ticket_payload()
    payload["steps"] = [{"id": "s1", "action": "teleport"}]
    with pytest.raises(ValidationError, match="action"):
        BugTicket.model_validate(payload)


def test_duplicate_step_ids_are_rejected() -> None:
    payload = ticket_payload()
    payload["preconditions"] = [{"id": "s1", "action": "goto", "url": "/"}]
    with pytest.raises(ValidationError, match="Duplicate step id"):
        BugTicket.model_validate(payload)


def test_criterion_must_reference_assertion_steps() -> None:
    payload = ticket_payload()
    payload["acceptance_criteria"] = [{"id": "AC1", "description": "x", "step_ids": ["s2"]}]
    with pytest.raises(ValidationError, match="action step"):
        BugTicket.model_validate(payload)


def test_criterion_must_reference_existing_steps() -> None:
    payload = ticket_payload()
    payload["acceptance_criteria"] = [{"id": "AC1", "description": "x", "step_ids": ["nope"]}]
    with pytest.raises(ValidationError, match="unknown step"):
        BugTicket.model_validate(payload)


def test_scenario_has_no_bug_fields() -> None:
    scenario = Scenario.model_validate(
        {
            "id": "smoke",
            "title": "Smoke",
            "url": "http://localhost/",
            "steps": [{"id": "n1", "action": "expect_url", "pattern": "**/"}],
        }
    )
    assert scenario.steps[0].is_assertion


def test_every_step_type_has_a_literal_action() -> None:
    actions = [action_name(step_type) for step_type in STEP_TYPES]
    assert len(actions) == len(set(actions))
    assert "click" in actions
    assert "expect_request" in actions


def test_default_titles_mask_secrets() -> None:
    step = FillStep(id="s1", target=Target(label="Password"), value="hunter2", secret=True)
    assert "hunter2" not in step.display_title()
    assert "***" in step.display_title()


def test_title_override_wins() -> None:
    step = ClickStep(id="s1", target=Target(test_id="save"), title="Press save")
    assert step.display_title() == "Press save"


def test_dialog_step_uses_type_alias() -> None:
    step = ExpectDialogStep.model_validate(
        {"id": "d1", "action": "expect_dialog", "type": "confirm"}
    )
    assert step.dialog_type == "confirm"
    assert step.model_dump(by_alias=True)["type"] == "confirm"


def test_wait_for_requires_exactly_one_mode() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        WaitForStep(id="w1")
    with pytest.raises(ValidationError, match="exactly one"):
        WaitForStep(id="w1", target=Target(css="body"), load_state="load")


def test_role_target_validates_role() -> None:
    with pytest.raises(ValidationError):
        RoleTarget(role="spaceship")
