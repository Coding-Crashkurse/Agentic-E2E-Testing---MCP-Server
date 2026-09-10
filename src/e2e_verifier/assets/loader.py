from __future__ import annotations

from functools import cache
from importlib import resources


class Assets:
    @staticmethod
    @cache
    def hud_script() -> str:
        return Assets._read("hud.js")

    @staticmethod
    @cache
    def discover_script() -> str:
        return Assets._read("discover.js")

    @staticmethod
    def _read(name: str) -> str:
        return resources.files("e2e_verifier.assets").joinpath(name).read_text(encoding="utf-8")
