from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

REGEX_PREFIX = "re:"


class UrlPattern:
    def __init__(self, pattern: str) -> None:
        self._pattern = pattern
        if pattern.startswith(REGEX_PREFIX):
            self._regex = re.compile(pattern[len(REGEX_PREFIX) :])
            self._is_regex = True
        else:
            self._regex = re.compile(self._glob_to_regex(pattern))
            self._is_regex = False

    @property
    def regex(self) -> re.Pattern[str]:
        return self._regex

    def matches(self, url: str) -> bool:
        if self._is_regex:
            return self._regex.search(url) is not None
        return self._regex.fullmatch(url) is not None

    def __str__(self) -> str:
        return self._pattern

    @staticmethod
    def _glob_to_regex(glob: str) -> str:
        parts: list[str] = []
        index = 0
        while index < len(glob):
            char = glob[index]
            if glob.startswith("**", index):
                parts.append(".*")
                index += 2
                continue
            if char == "*":
                parts.append("[^/]*")
            elif char == "?":
                parts.append(".")
            else:
                parts.append(re.escape(char))
            index += 1
        return "".join(parts)


class UrlRewriter:
    def __init__(self, ticket_url: str, override: str | None = None) -> None:
        self._original = ticket_url
        self._override = override
        self._original_host = self._netloc_key(ticket_url)
        self._target = self._apply_override(ticket_url)

    @property
    def target_url(self) -> str:
        return self._target

    @property
    def original_url(self) -> str:
        return self._original

    def resolve(self, url: str) -> str:
        absolute = urljoin(self._target, url)
        if self._override is not None and self._netloc_key(absolute) == self._original_host:
            return self._apply_override(absolute)
        return absolute

    def _apply_override(self, url: str) -> str:
        if self._override is None:
            return url
        base = urlsplit(self._override)
        parts = urlsplit(url)
        return urlunsplit((base.scheme, base.netloc, parts.path, parts.query, parts.fragment))

    @staticmethod
    def _netloc_key(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{(parts.netloc or '').lower()}"
