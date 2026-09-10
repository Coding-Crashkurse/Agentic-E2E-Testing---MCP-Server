from __future__ import annotations

from collections.abc import Iterable
from fnmatch import fnmatchcase
from urllib.parse import urlsplit

from e2e_verifier.domain.errors import HostNotAllowedError

SCHEMES_WITHOUT_HOST = frozenset({"about", "data", "blob", "javascript"})


class HostAllowlist:
    def __init__(self, patterns: Iterable[str], allow_any: bool = False) -> None:
        self._patterns = [self._normalize(pattern) for pattern in patterns if pattern.strip()]
        self._allow_any = allow_any

    @property
    def patterns(self) -> list[str]:
        return list(self._patterns)

    @property
    def allow_any(self) -> bool:
        return self._allow_any

    def allows(self, url: str) -> bool:
        if self._allow_any:
            return True
        parts = urlsplit(url)
        if parts.scheme in SCHEMES_WITHOUT_HOST:
            return True
        host = parts.hostname
        if host is None:
            return False
        normalized = self._normalize(host)
        return any(fnmatchcase(normalized, pattern) for pattern in self._patterns)

    def ensure(self, url: str) -> None:
        if not self.allows(url):
            raise HostNotAllowedError(url)

    @staticmethod
    def _normalize(host: str) -> str:
        return host.strip().lower().strip("[]")
