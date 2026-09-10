from __future__ import annotations

import pytest
from pydantic import ValidationError

from e2e_verifier.domain.steps import RoleTarget, Target, TextTarget


def test_exactly_one_strategy_required() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        Target()
    with pytest.raises(ValidationError, match="exactly one"):
        Target(label="Name", css="#name")


def test_negative_nth_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Target(css="li", nth=-1)


def test_within_is_recursive() -> None:
    target = Target(
        role=RoleTarget(role="button", name="Save"),
        within=Target(css="form", within=Target(test_id="main")),
    )
    assert target.strategy == "role"
    assert target.within is not None
    assert target.within.within is not None
    assert target.within.within.strategy == "test_id"


def test_describe_mentions_refinements() -> None:
    target = Target(text=TextTarget(text="Save"), has_text="Sa", nth=1, within=Target(css="form"))
    described = target.describe()
    assert 'text "Save"' in described
    assert "#2" in described
    assert "within css form" in described
