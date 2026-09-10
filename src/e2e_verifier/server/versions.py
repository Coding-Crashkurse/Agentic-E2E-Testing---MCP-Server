from __future__ import annotations

from importlib import metadata

from e2e_verifier.domain.common import FrozenModel


class VersionInfo(FrozenModel):
    server: str
    fastmcp: str
    playwright: str

    @classmethod
    def detect(cls) -> VersionInfo:
        return cls(
            server=cls._version("e2e-verifier"),
            fastmcp=cls._version("fastmcp"),
            playwright=cls._version("playwright"),
        )

    @staticmethod
    def _version(distribution: str) -> str:
        try:
            return metadata.version(distribution)
        except metadata.PackageNotFoundError:
            return "unknown"
