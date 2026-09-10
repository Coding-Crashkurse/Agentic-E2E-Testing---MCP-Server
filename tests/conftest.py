from __future__ import annotations

import json
import threading
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from e2e_verifier.browser.session import BrowserPool
from e2e_verifier.domain.enums import Outcome, RunKind, RunMode, StepPhase, StepStatus, Verdict
from e2e_verifier.domain.result import (
    ArtifactSet,
    BrowserInfo,
    CriterionResult,
    Observations,
    RunResult,
    StepError,
    StepResult,
)
from e2e_verifier.domain.settings import Settings
from e2e_verifier.domain.ticket import BugTicket, Viewport

SITE_DIR = Path(__file__).parent / "fixtures" / "site"
SLOW_DELAY_S = 8.0


class FixtureHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path == "/api/settings":
            length = int(self.headers.get("content-length", "0"))
            self.rfile.read(length)
            payload = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def do_GET(self) -> None:
        if self.path.startswith("/slow"):
            time.sleep(SLOW_DELAY_S)
            self.path = "/index.html"
        elif self.path.startswith("/redirect-external"):
            self.send_response(302)
            address = self.server.server_address
            port = address[1] if isinstance(address, tuple) else 0
            self.send_header("location", f"http://localhost:{port}/")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, fmt: str, *args: Any) -> None:
        return


class FixtureSite:
    def __init__(self) -> None:
        handler = partial(FixtureHandler, directory=str(SITE_DIR))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture(scope="session")
def fixture_site() -> Iterator[FixtureSite]:
    site = FixtureSite()
    site.start()
    yield site
    site.stop()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        artifact_dir=tmp_path / "artifacts",
        allowed_hosts=["127.0.0.1"],
        headless=True,
        default_step_timeout_ms=4000,
        default_run_timeout_s=60,
        hud_language="en",
        fixture_dir=SITE_DIR,
    )


@pytest.fixture
async def pool() -> AsyncIterator[BrowserPool]:
    browser_pool = BrowserPool()
    yield browser_pool
    await browser_pool.stop()


class TicketFactory:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def happy(self) -> BugTicket:
        return BugTicket.model_validate(
            {
                "id": "FIX-1",
                "title": "Save shows a toast and sends a request",
                "url": f"{self.base_url}/index.html",
                "steps": [
                    {"id": "s1", "action": "fill", "target": {"label": "Name"}, "value": "Anna"},
                    {
                        "id": "s2",
                        "action": "click",
                        "target": {"role": {"role": "button", "name": "Save"}},
                    },
                    {
                        "id": "s3",
                        "action": "expect_text",
                        "target": {"test_id": "toast"},
                        "text": "Saved",
                        "timeout_ms": 3000,
                    },
                    {
                        "id": "s4",
                        "action": "expect_request",
                        "method": "POST",
                        "url_pattern": "**/api/settings",
                        "status": 200,
                        "timeout_ms": 3000,
                    },
                    {"id": "s5", "action": "expect_no_console_errors"},
                    {
                        "id": "s6",
                        "action": "expect_storage",
                        "kind": "local",
                        "key": "name",
                        "value": "Anna",
                    },
                ],
                "expected": "Toast Saved appears and the settings are posted",
                "actual": "-",
                "acceptance_criteria": [
                    {"id": "AC1", "description": "toast appears", "step_ids": ["s3"]},
                    {"id": "AC2", "description": "settings are posted", "step_ids": ["s4"]},
                    {
                        "id": "AC3",
                        "description": "no errors, value stored",
                        "step_ids": ["s5", "s6"],
                    },
                ],
            }
        )

    def broken_button(self) -> BugTicket:
        return BugTicket.model_validate(
            {
                "id": "BUG-7",
                "title": "Delete button does nothing",
                "url": f"{self.base_url}/index.html",
                "steps": [
                    {
                        "id": "s1",
                        "action": "click",
                        "target": {"role": {"role": "button", "name": "Delete"}},
                    },
                    {
                        "id": "s2",
                        "action": "expect_visible",
                        "target": {"test_id": "toast"},
                        "timeout_ms": 1500,
                    },
                    {
                        "id": "s3",
                        "action": "expect_request",
                        "method": "POST",
                        "url_pattern": "**/api/delete",
                        "timeout_ms": 1500,
                    },
                ],
                "expected": "A confirmation toast appears and a DELETE request is sent",
                "actual": "Nothing happens",
                "acceptance_criteria": [
                    {"id": "AC1", "description": "toast appears", "step_ids": ["s2"]},
                    {"id": "AC2", "description": "request is sent", "step_ids": ["s3"]},
                ],
            }
        )


@pytest.fixture
def tickets(fixture_site: FixtureSite) -> TicketFactory:
    return TicketFactory(fixture_site.base_url)


class ResultFactory:
    @staticmethod
    def sample(run_id: str = "01J9X0Q3M6WZ2M8Y4K7P1R5T9V") -> RunResult:
        started = datetime(2026, 9, 10, 10, 52, 13, tzinfo=UTC)
        finished = datetime(2026, 9, 10, 10, 52, 24, tzinfo=UTC)
        error = StepError(category="assertion", message="Timed out waiting for toast")
        return RunResult(
            run_id=run_id,
            kind=RunKind.TICKET,
            ticket_id="WEB-142",
            title="Save button does nothing",
            mode=RunMode.REPRODUCE,
            outcome=Outcome.CRITERIA_NOT_MET,
            verdict=Verdict.REPRODUCED,
            summary="Bug reproduced: step s3 failed",
            started_at=started,
            finished_at=finished,
            duration_ms=11000,
            video_offset_uncertainty_ms=300,
            browser=BrowserInfo(
                name="chromium", version="140.0", headless=True, viewport=Viewport()
            ),
            target_url="http://127.0.0.1:5173/settings",
            steps=[
                StepResult(
                    index=1,
                    id="s1",
                    phase=StepPhase.STEPS,
                    action="fill",
                    title='Fill field "Name" with "Anna"',
                    status=StepStatus.PASSED,
                    started_offset_ms=1240,
                    ended_offset_ms=1512,
                    screenshot="screenshots/001_passed.png",
                    trace_group="Step 1/3: Fill",
                ),
                StepResult(
                    index=2,
                    id="s2",
                    phase=StepPhase.STEPS,
                    action="click",
                    title='Click button "Save"',
                    status=StepStatus.PASSED,
                    started_offset_ms=1530,
                    ended_offset_ms=1701,
                    trace_group="Step 2/3: Click",
                ),
                StepResult(
                    index=3,
                    id="s3",
                    phase=StepPhase.STEPS,
                    action="expect_visible",
                    title="Expect toast",
                    status=StepStatus.FAILED,
                    started_offset_ms=1720,
                    ended_offset_ms=6744,
                    error=error,
                    failure_screenshot="screenshots/003_failure_fullpage.png",
                    trace_group="Step 3/3: Expect toast",
                ),
            ],
            acceptance_criteria=[
                CriterionResult(
                    id="AC1", description="toast", status="not_met", step_ids=["s3"], evidence=None
                )
            ],
            observations=Observations(
                console_errors=0,
                page_errors=0,
                failed_requests=0,
                requests_total=14,
                requests_after_step={"s2": 0},
            ),
            artifacts=ArtifactSet(
                dir="C:/runs/x",
                video="video.webm",
                video_mp4=None,
                trace="trace.zip",
                report="report.md",
                chapters="chapters.vtt",
                console_log="console.jsonl",
                network_log="network.jsonl",
                har=None,
                screenshots=["screenshots/001_passed.png"],
            ),
        )


@pytest.fixture
def sample_result() -> RunResult:
    return ResultFactory.sample()
