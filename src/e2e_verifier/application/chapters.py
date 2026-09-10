from __future__ import annotations

from e2e_verifier.domain.result import RunResult


class ChapterWriter:
    def build(self, result: RunResult) -> str:
        lines = ["WEBVTT", ""]
        for step in result.steps:
            if step.started_offset_ms is None:
                continue
            start = max(step.started_offset_ms, 0)
            end = step.ended_offset_ms if step.ended_offset_ms is not None else start + 1
            end = max(end, start + 1)
            lines.extend(
                [
                    str(step.index),
                    f"{self._stamp(start)} --> {self._stamp(end)}",
                    f"[{step.status}] {step.title}",
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _stamp(offset_ms: int) -> str:
        total_seconds, millis = divmod(offset_ms, 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
