from __future__ import annotations

import base64
import json

import pytest
from fastmcp import Client
from mcp.types import ImageContent, TextContent

from e2e_verifier.application.store import ArtifactNames
from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.enums import AnnotationTone, StepStatus, Verdict
from e2e_verifier.domain.options import RunOptions
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.steps import ClickStep, ExpectTextStep, Target
from e2e_verifier.server.app import ServerFactory
from tests.conftest import FixtureSite

pytestmark = pytest.mark.integration


async def test_interactive_session_records_video_and_annotations(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    manager = factory.interactive
    session, first = await manager.open(
        f"{fixture_site.base_url}/index.html", RunOptions(post_roll_ms=200)
    )
    assert first.step.status is StepStatus.PASSED
    assert first.title == "Fixture App"

    clicked = await session.act(ClickStep(id="click-delete", target=Target(test_id="delete")))
    assert clicked.step.status is StepStatus.PASSED
    missing = await session.act(
        ExpectTextStep(id="toast", target=Target(test_id="toast"), text="Deleted", timeout_ms=1000)
    )
    assert missing.step.status is StepStatus.FAILED
    assert missing.step.error is not None
    assert missing.step.error.highlight_target is not None
    assert missing.step.error.highlight_target.rect is not None

    note = await session.annotate(
        "Delete does nothing", Target(test_id="delete"), AnnotationTone.FAILURE, 300
    )
    assert note.rect is not None
    state = await session._session.hud.get_state()  # type: ignore[attr-defined]
    assert state is not None
    assert state["annotation"]["message"] == "Delete does nothing"

    inspected = await session.inspect("Save", 5)
    assert any(candidate.test_id == "save" for candidate in inspected.candidates)
    inline = await session.inline_screenshot()
    assert inline[:2] == b"\xff\xd8"

    result = await manager.close(session.session_id, None, None)
    assert result.verdict is Verdict.FAILED
    assert (session.run_dir / ArtifactNames.VIDEO).stat().st_size > 0
    assert (session.run_dir / ArtifactNames.TRACE).stat().st_size > 0
    assert any("note001_failure" in shot for shot in result.artifacts.screenshots)
    assert factory.runs.get(session.session_id).run_id == session.session_id


async def test_session_tools_through_mcp_client(
    settings: Settings, pool: BrowserPool, fixture_site: FixtureSite
) -> None:
    factory = ServerFactory(settings, pool)
    async with Client(factory.build()) as client:
        opened = await client.call_tool(
            "session_open",
            {"url": f"{fixture_site.base_url}/index.html", "options": {"post_roll_ms": 0}},
        )
        assert isinstance(opened.content[0], TextContent)
        assert isinstance(opened.content[1], ImageContent)
        payload = json.loads(opened.content[0].text)
        session_id = payload["session"]["session_id"]
        assert payload["first_step"]["step"]["status"] == "passed"
        assert base64.b64decode(opened.content[1].data)[:2] == b"\xff\xd8"

        acted = await client.call_tool(
            "session_act",
            {
                "session_id": session_id,
                "step": {"id": "s1", "action": "click", "target": {"test_id": "top-button"}},
            },
        )
        act_payload = json.loads(acted.content[0].text)
        assert act_payload["step"]["status"] == "passed"
        assert isinstance(acted.content[1], ImageContent)

        checked = await client.call_tool(
            "session_act",
            {
                "session_id": session_id,
                "step": {
                    "id": "s2",
                    "action": "expect_text",
                    "target": {"test_id": "toast"},
                    "text": "Top clicked",
                },
                "include_screenshot": False,
            },
        )
        assert len(checked.content) == 1
        assert json.loads(checked.content[0].text)["step"]["status"] == "passed"

        annotated = await client.call_tool(
            "session_annotate",
            {
                "session_id": session_id,
                "message": "toast appeared as expected",
                "target": {"test_id": "toast"},
                "tone": "success",
                "hold_ms": 100,
            },
        )
        assert json.loads(annotated.content[0].text)["tone"] == "success"

        listed = await client.call_tool("session_list", {})
        assert listed.structured_content is not None
        assert listed.structured_content["result"][0]["session_id"] == session_id

        inspected = await client.call_tool(
            "session_inspect", {"session_id": session_id, "query": "Delete"}
        )
        assert inspected.structured_content is not None
        assert inspected.structured_content["candidates"]

        closed = await client.call_tool(
            "session_close",
            {"session_id": session_id, "verdict": "passed", "summary": "top button works"},
        )
        assert closed.structured_content is not None
        assert closed.structured_content["verdict"] == "passed"
        assert closed.structured_content["summary"] == "top button works"

        artifact = await client.call_tool("get_artifact", {"run_id": session_id, "kind": "report"})
        assert artifact.content
        schema = await client.call_tool("get_schema", {"kind": "step"})
        assert schema.structured_content is not None
        assert "oneOf" in json.dumps(schema.structured_content)
