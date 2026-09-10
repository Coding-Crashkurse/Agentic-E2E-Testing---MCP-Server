from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...

    def monotonic_ms(self) -> int: ...

    def epoch_ms(self) -> int: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic_ms(self) -> int:
        return int(time.monotonic() * 1000)

    def epoch_ms(self) -> int:
        return int(time.time() * 1000)
