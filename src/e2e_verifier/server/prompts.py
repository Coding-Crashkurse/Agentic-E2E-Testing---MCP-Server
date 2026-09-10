from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import PromptError

from e2e_verifier.application.registry import RunRegistry
from e2e_verifier.application.store import ArtifactNames, ArtifactStore
from e2e_verifier.domain.enums import StepStatus
from e2e_verifier.domain.errors import VerifierError
from e2e_verifier.domain.result import RunResult
from e2e_verifier.domain.ticket import BugTicket

LOG_TAIL_LINES = 40


class VerifierPrompts:
    def __init__(self, store: ArtifactStore, runs: RunRegistry) -> None:
        self._store = store
        self._runs = runs

    def register(self, mcp: FastMCP[Any]) -> None:
        mcp.prompt(
            self.ticket_from_report,
            name="ticket_from_report",
            description="Turn a free-text bug report into a BugTicket JSON for run_ticket.",
        )
        mcp.prompt(
            self.analyze_run,
            name="analyze_run",
            description=(
                "Analyze a finished run: root-cause hypothesis and where to look in the trace."
            ),
        )
        mcp.prompt(
            self.refine_target,
            name="refine_target",
            description=(
                "Propose a more precise Target for a step that failed to locate its element."
            ),
        )

    async def ticket_from_report(self, report_text: str, base_url: str) -> str:
        schema = json.dumps(BugTicket.model_json_schema(by_alias=True))
        return (
            "Convert the following bug report into a BugTicket JSON document that the "
            "e2e-verifier MCP server can execute with run_ticket.\n\n"
            f"Base URL of the site under test: {base_url}\n\n"
            "Rules:\n"
            "- Every reproduction step becomes one action step (goto, click, fill, ...).\n"
            "- Every acceptance criterion becomes one or more assertion steps "
            "(expect_visible, expect_text, expect_request, expect_no_console_errors, ...) "
            "and is listed in acceptance_criteria with the ids of those assertion steps.\n"
            "- Prefer targets in this order: role+name, label, test_id, text, css, xpath. "
            "Call discover_elements on the page when you are unsure which target exists.\n"
            "- Use expect_request when the report mentions saving, submitting or loading data.\n"
            "- Keep step ids short and unique (s1, s2, ...). Do not include secrets.\n"
            "- Validate the result with validate_ticket before calling run_ticket.\n\n"
            f"JSON schema of BugTicket:\n{schema}\n\n"
            f"Bug report:\n{report_text}\n"
        )

    async def analyze_run(self, run_id: str) -> str:
        result, run_dir = self._load(run_id)
        console = self._tail(run_dir / ArtifactNames.CONSOLE)
        network = self._tail(run_dir / ArtifactNames.NETWORK)
        failed = next(
            (step for step in result.steps if step.status in {StepStatus.FAILED, StepStatus.ERROR}),
            None,
        )
        focus = (
            f'Open trace group "{failed.trace_group}" first.'
            if failed and failed.trace_group
            else ""
        )
        return (
            f"Analyze run {run_id} of ticket {result.ticket_id} ({result.title}).\n"
            f"Verdict: {result.verdict}. Summary: {result.summary}\n\n"
            "Tasks:\n"
            "1. State the most likely root cause from the failed step, console and network data.\n"
            "2. Say which step to open in the Playwright trace viewer and why. "
            f"{focus}\n"
            "3. List what additional assertion would make the ticket more precise.\n\n"
            f"result.json:\n{result.model_dump_json(indent=2)}\n\n"
            f"Last console entries:\n{console}\n\nLast network entries:\n{network}\n"
        )

    async def refine_target(self, run_id: str, step_id: str) -> str:
        result, _ = self._load(run_id)
        step = next((item for item in result.steps if item.id == step_id), None)
        if step is None:
            raise PromptError(f"Step {step_id} not found in run {run_id}")
        error = step.error
        candidates = "\n".join(
            f"- {candidate}" for candidate in (error.candidates if error else [])
        )
        return (
            f"Step {step.id} ({step.title}) of run {run_id} could not resolve its target.\n"
            f"Status: {step.status}; error: {error.message if error else '-'}\n"
            f"Locator used: {error.locator if error else '-'}\n"
            f"Candidates reported by Playwright:\n{candidates or '- none'}\n\n"
            "Propose a more precise Target JSON (role+name with exact=true, label, test_id, "
            "or a within/has_text/nth refinement). Call discover_elements on the target URL "
            f"({result.target_url}) with a query for the element text to list real candidates.\n"
        )

    def _load(self, run_id: str) -> tuple[RunResult, Any]:
        try:
            result = self._runs.get(run_id)
            run_dir = self._store.run_dir(run_id)
        except VerifierError as exc:
            raise PromptError(str(exc)) from exc
        return result, run_dir

    @staticmethod
    def _tail(path: Any) -> str:
        if not path.is_file():
            return "-"
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[-LOG_TAIL_LINES:]) or "-"
