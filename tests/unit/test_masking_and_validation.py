from __future__ import annotations

from pathlib import Path

from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.validation import TicketValidator
from e2e_verifier.domain.masking import SecretMasker
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import BugTicket


def ticket(**overrides: object) -> BugTicket:
    payload: dict[str, object] = {
        "id": "T",
        "title": "t",
        "url": "http://localhost:5173/",
        "steps": [
            {
                "id": "f",
                "action": "fill",
                "target": {"label": "pw"},
                "value": "hunter2",
                "secret": True,
            },
            {"id": "c", "action": "click", "target": {"css": "#go"}},
            {"id": "z", "action": "sleep", "ms": 200},
            {"id": "a", "action": "expect_visible", "target": {"test_id": "ok"}},
            {"id": "b", "action": "expect_no_console_errors"},
        ],
        "expected": "x",
        "acceptance_criteria": [{"id": "AC1", "description": "d", "step_ids": ["a"]}],
    }
    payload.update(overrides)
    return BugTicket.model_validate(payload)


def test_masker_replaces_secret_values_everywhere() -> None:
    masker = SecretMasker()
    source = ticket()
    assert masker.secret_values(source) == ["hunter2"]
    masked = masker.mask_source(source)
    assert "hunter2" not in masked.model_dump_json()
    assert masker.mask_text("fill hunter2 into pw", ["hunter2"]) == "fill *** into pw"


def test_validator_reports_warnings_for_brittle_and_unreferenced_steps(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, fixture_dir=tmp_path)
    validator = TicketValidator(settings, HostAllowlist(["localhost"]))
    report = validator.validate(ticket(), RunOptions())
    assert report.ok
    codes = sorted(issue.code for issue in report.warnings)
    assert codes == ["brittle_selector", "secret_in_trace", "sleep_step", "unreferenced_assertion"]


def test_validator_rejects_foreign_hosts_and_large_timeouts() -> None:
    settings = Settings(_env_file=None, max_run_timeout_s=60)
    validator = TicketValidator(settings, HostAllowlist(["localhost"]))
    source = ticket(
        url="http://evil.test/",
        steps=[
            {"id": "g", "action": "goto", "url": "http://also-evil.test/"},
            {"id": "a", "action": "expect_visible", "target": {"test_id": "ok"}},
        ],
    )
    report = validator.validate(source, RunOptions(run_timeout_s=600))
    assert not report.ok
    codes = sorted(issue.code for issue in report.errors)
    assert codes == ["host_not_allowed", "host_not_allowed", "run_timeout_too_large"]


def test_validator_checks_fixture_paths(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("x", encoding="utf-8")
    settings = Settings(_env_file=None, fixture_dir=tmp_path)
    validator = TicketValidator(settings, HostAllowlist(["localhost"]))
    good = ticket(
        steps=[
            {"id": "u", "action": "upload_file", "target": {"css": "input"}, "path": "ok.txt"},
            {"id": "a", "action": "expect_visible", "target": {"test_id": "ok"}},
        ]
    )
    assert validator.validate(good).ok
    bad = ticket(
        steps=[
            {
                "id": "u",
                "action": "upload_file",
                "target": {"css": "input"},
                "path": "../etc/passwd",
            },
            {"id": "a", "action": "expect_visible", "target": {"test_id": "ok"}},
        ],
        environment={"storage_state_path": "missing.json"},
    )
    report = validator.validate(bad)
    assert sorted(issue.code for issue in report.errors) == ["storage_state_path", "upload_path"]
