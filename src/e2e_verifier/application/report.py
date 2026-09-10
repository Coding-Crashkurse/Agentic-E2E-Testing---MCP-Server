from __future__ import annotations

from e2e_verifier.application.compiler import ExecutionPlan
from e2e_verifier.domain.enums import RunKind
from e2e_verifier.domain.result import RunResult, StepResult


def format_offset(offset_ms: int | None) -> str:
    if offset_ms is None:
        return "-"
    total_seconds, millis = divmod(max(offset_ms, 0), 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{millis // 100}"


class ReportBuilder:
    def build(self, result: RunResult, plan: ExecutionPlan) -> str:
        sections = [
            self._header(result),
            self._summary(result, plan),
            self._criteria(result),
            self._steps(result),
            self._observations(result),
            self._artifacts(result),
            self._input(plan),
        ]
        return "\n\n".join(section for section in sections if section) + "\n"

    @staticmethod
    def _header(result: RunResult) -> str:
        browser = result.browser
        mode = "headless" if browser.headless else "headed"
        stamp = result.started_at.strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"# {result.ticket_id} - {result.title}\n\n"
            f"Verdict: **{result.verdict}** (mode `{result.mode}`) · Run `{result.run_id}` · "
            f"{stamp} · {browser.name} {browser.version or ''} {mode}"
        )

    @staticmethod
    def _summary(result: RunResult, plan: ExecutionPlan) -> str:
        lines = ["## Summary", "", result.summary]
        if plan.kind is RunKind.TICKET:
            lines.extend(
                ["", f"Expected: {plan.expected or '-'}", "", f"Actual: {plan.actual or '-'}"]
            )
        if result.warnings:
            lines.extend(["", "Warnings:", *[f"- {warning}" for warning in result.warnings]])
        return "\n".join(lines)

    @staticmethod
    def _criteria(result: RunResult) -> str:
        lines = [
            "## Acceptance criteria",
            "",
            "| ID | Criterion | Status | Evidence |",
            "|---|---|---|---|",
        ]
        for criterion in result.acceptance_criteria:
            evidence = "-"
            if criterion.evidence is not None:
                parts = [f"video {format_offset(criterion.evidence.video_offset_ms)}"]
                if criterion.evidence.screenshot:
                    parts.append(criterion.evidence.screenshot)
                if criterion.evidence.trace_group:
                    parts.append(f'trace group "{criterion.evidence.trace_group}"')
                evidence = ", ".join(parts)
            lines.append(
                f"| {criterion.id} | {criterion.description} | {criterion.status} | {evidence} |"
            )
        return "\n".join(lines)

    def _steps(self, result: RunResult) -> str:
        lines = [
            "## Steps",
            "",
            "| # | Step | Status | Video | Duration | Detail |",
            "|---|---|---|---|---|---|",
        ]
        lines.extend(self._step_row(step) for step in result.steps)
        return "\n".join(lines)

    @staticmethod
    def _step_row(step: StepResult) -> str:
        duration = f"{step.duration_ms} ms" if step.duration_ms is not None else "-"
        detail = step.error.message.replace("\n", " ") if step.error else ""
        if step.error and step.error.highlight_target and step.error.highlight_target.rect:
            detail = f"{detail} (highlighted {step.error.highlight_target.source} "
            detail += f"{step.error.highlight_target.step_id})"
        title = step.title.replace("|", "\\|")
        detail = detail.replace("|", "\\|")
        return (
            f"| {step.index} | {title} | {step.status} | "
            f"{format_offset(step.started_offset_ms)} | {duration} | {detail} |"
        )

    @staticmethod
    def _observations(result: RunResult) -> str:
        observed = result.observations
        lines = [
            "## Observations",
            "",
            f"- Console errors: {observed.console_errors}",
            f"- Page errors: {observed.page_errors}",
            f"- Failed requests: {observed.failed_requests}",
            f"- Requests total: {observed.requests_total}",
        ]
        for step_id, count in observed.requests_after_step.items():
            lines.append(f"- Requests after step {step_id}: {count}")
        if observed.truncated:
            lines.append("- Logs were truncated at the configured limit")
        return "\n".join(lines)

    @staticmethod
    def _artifacts(result: RunResult) -> str:
        artifacts = result.artifacts
        lines = ["## Artifacts", "", f"Directory: `{artifacts.dir}`", ""]
        if artifacts.video:
            lines.append(f"- Video: {artifacts.video} (chapters: {artifacts.chapters or '-'})")
        if artifacts.video_mp4:
            lines.append(f"- Video (mp4): {artifacts.video_mp4}")
        if artifacts.trace:
            lines.append(f"- Trace: {artifacts.trace} (open with `playwright show-trace`)")
        if artifacts.console_log:
            lines.append(f"- Console log: {artifacts.console_log}")
        if artifacts.network_log:
            lines.append(f"- Network log: {artifacts.network_log}")
        if artifacts.har:
            lines.append(f"- HAR: {artifacts.har}")
        lines.extend(f"- Screenshot: {shot}" for shot in artifacts.screenshots)
        return "\n".join(lines)

    @staticmethod
    def _input(plan: ExecutionPlan) -> str:
        payload = plan.source.model_dump_json(indent=2, by_alias=True)
        return (
            "## Input\n\n<details>\n<summary>ticket.json</summary>\n\n"
            f"```json\n{payload}\n```\n\n</details>"
        )
