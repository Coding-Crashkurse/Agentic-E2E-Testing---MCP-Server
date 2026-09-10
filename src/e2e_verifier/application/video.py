from __future__ import annotations

import asyncio
from asyncio.subprocess import DEVNULL, PIPE
from pathlib import Path

CONVERSION_TIMEOUT_S = 180


class VideoConverter:
    def __init__(self, ffmpeg_path: Path | None) -> None:
        self._ffmpeg = ffmpeg_path

    @property
    def available(self) -> bool:
        return self._ffmpeg is not None

    async def to_mp4(self, source: Path, target: Path) -> str | None:
        if self._ffmpeg is None:
            return None
        arguments = [
            str(self._ffmpeg),
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *arguments, stdout=DEVNULL, stderr=PIPE, stdin=DEVNULL
            )
            async with asyncio.timeout(CONVERSION_TIMEOUT_S):
                _, stderr = await process.communicate()
        except (OSError, TimeoutError) as exc:
            return f"mp4 conversion failed: {exc}"
        if process.returncode != 0:
            return f"mp4 conversion failed: {stderr.decode(errors='replace').strip()[:300]}"
        return None
