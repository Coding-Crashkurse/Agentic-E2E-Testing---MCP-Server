from __future__ import annotations

import base64
import json

import pytest
from fastmcp import Client
from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents

from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.settings import Settings
from e2e_verifier.server.app import ServerFactory
from tests.conftest import TicketFactory

pytestmark = pytest.mark.integration

EXPECTED_TOOLS = {
    "get_schema",
    "validate_ticket",
    "run_ticket",
    "run_scenario",
    "get_run",
    "list_runs",
    "get_artifact",
    "delete_run",
    "probe_target",
    "discover_elements",
    "server_info",
}


async def test_full_roundtrip_through_mcp_client(
    settings: Settings, pool: BrowserPool, tickets: TicketFactory
) -> None:
    factory = ServerFactory(settings, pool)
    ticket = tickets.broken_button().model_dump(mode="json", by_alias=True)
    async with Client(factory.build()) as client:
        tools = {tool.name for tool in await client.list_tools()}
        assert tools >= EXPECTED_TOOLS
        run_tool = next(tool for tool in await client.list_tools() if tool.name == "run_ticket")
        assert "ctx" not in run_tool.inputSchema.get("properties", {})

        validation = await client.call_tool("validate_ticket", {"ticket": ticket})
        assert validation.structured_content is not None
        assert validation.structured_content["ok"] is True

        schema = await client.call_tool("get_schema", {"kind": "ticket"})
        assert schema.structured_content is not None
        assert "acceptance_criteria" in json.dumps(schema.structured_content)

        progress: list[float] = []

        async def on_progress(value: float, total: float | None, message: str | None) -> None:
            progress.append(value)

        run = await client.call_tool(
            "run_ticket",
            {
                "ticket": ticket,
                "options": {"mode": "reproduce", "failure_hold_ms": 0, "post_roll_ms": 0},
            },
            progress_handler=on_progress,
        )
        payload = run.structured_content
        assert payload is not None
        assert payload["verdict"] == "reproduced"
        run_id = payload["run_id"]
        assert progress

        listed = await client.call_tool("list_runs", {"limit": 5})
        assert listed.structured_content is not None
        assert listed.structured_content["result"][0]["run_id"] == run_id

        fetched = await client.call_tool("get_run", {"run_id": run_id})
        assert fetched.structured_content is not None
        assert fetched.structured_content["run_id"] == run_id

        report = await client.read_resource(f"runs://{run_id}/report")
        assert isinstance(report[0], TextResourceContents)
        assert "**reproduced**" in report[0].text

        trace = await client.call_tool("get_artifact", {"run_id": run_id, "kind": "trace"})
        resource = trace.content[0]
        assert isinstance(resource, EmbeddedResource)
        assert isinstance(resource.resource, BlobResourceContents)
        assert base64.b64decode(resource.resource.blob)[:2] == b"PK"

        screenshot = await client.read_resource(f"runs://{run_id}/screenshots/0")
        assert isinstance(screenshot[0], BlobResourceContents)
        assert base64.b64decode(screenshot[0].blob)[:4] == b"\x89PNG"

        info = await client.call_tool("server_info", {})
        assert info.structured_content is not None
        assert info.structured_content["runs_stored"] == 1

        deleted = await client.call_tool("delete_run", {"run_id": run_id})
        assert deleted.structured_content is not None
        assert deleted.structured_content["deleted"] is True
        assert factory.runs.count() == 0
