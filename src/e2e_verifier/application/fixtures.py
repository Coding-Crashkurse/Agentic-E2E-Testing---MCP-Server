from __future__ import annotations

from pathlib import Path

from e2e_verifier.domain.errors import FixturePathError


class FixturePaths:
    def __init__(self, fixture_dir: Path | None) -> None:
        self._root = fixture_dir.resolve() if fixture_dir is not None else None

    @property
    def configured(self) -> bool:
        return self._root is not None

    def resolve(self, relative: str) -> Path:
        if self._root is None:
            raise FixturePathError(relative)
        candidate = (self._root / relative).resolve()
        if not candidate.is_relative_to(self._root) or not candidate.exists():
            raise FixturePathError(relative)
        return candidate
