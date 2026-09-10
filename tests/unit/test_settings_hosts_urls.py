from __future__ import annotations

import pytest

from e2e_verifier.application.hosts import HostAllowlist
from e2e_verifier.application.urls import UrlPattern, UrlRewriter
from e2e_verifier.domain.errors import HostNotAllowedError
from e2e_verifier.domain.settings import Settings


def test_settings_parse_comma_separated_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("E2E_ALLOWED_HOSTS", "localhost, app.local ,*.example.test")
    monkeypatch.setenv("E2E_HTTP_PORT", "9000")
    settings = Settings(_env_file=None)
    assert settings.allowed_hosts == ["localhost", "app.local", "*.example.test"]
    assert settings.http_port == 9000


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None, allowed_hosts=["localhost"])
    assert settings.browser == "chromium"
    assert settings.max_inline_artifact_bytes == 8 * 1024 * 1024


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("http://localhost:5173/x", True),
        ("http://LOCALHOST/", True),
        ("http://127.0.0.1:4173/", True),
        ("http://[::1]:8080/", True),
        ("http://shop.example.test/cart", True),
        ("http://evil.example.com/", False),
        ("https://example.test/", False),
        ("about:blank", True),
        ("data:text/html,hi", True),
    ],
)
def test_allowlist_matching(url: str, allowed: bool) -> None:
    allowlist = HostAllowlist(["localhost", "127.0.0.1", "[::1]", "*.example.test"])
    assert allowlist.allows(url) is allowed


def test_allowlist_ensure_raises_and_allow_any_bypasses() -> None:
    allowlist = HostAllowlist(["localhost"])
    with pytest.raises(HostNotAllowedError):
        allowlist.ensure("http://other/")
    assert HostAllowlist([], allow_any=True).allows("http://anything/")


@pytest.mark.parametrize(
    ("pattern", "url", "expected"),
    [
        ("**/api/settings", "http://h/api/settings", True),
        ("**/api/settings", "http://h/api/settings?x=1", False),
        ("**/api/*", "http://h/api/settings", True),
        ("**/api/*", "http://h/api/v1/settings", False),
        ("http://h/api/**", "http://h/api/v1/settings", True),
        ("re:/api/(settings|profile)$", "http://h/api/profile", True),
        ("re:^https", "http://h/", False),
    ],
)
def test_url_pattern(pattern: str, url: str, expected: bool) -> None:
    assert UrlPattern(pattern).matches(url) is expected


def test_url_rewriter_without_override_resolves_relative() -> None:
    rewriter = UrlRewriter("http://localhost:5173/settings")
    assert rewriter.target_url == "http://localhost:5173/settings"
    assert rewriter.resolve("/cart") == "http://localhost:5173/cart"
    assert rewriter.resolve("cart") == "http://localhost:5173/cart"


def test_url_rewriter_with_override_keeps_foreign_hosts() -> None:
    rewriter = UrlRewriter("http://localhost:5173/settings", "https://staging.test:8443")
    assert rewriter.target_url == "https://staging.test:8443/settings"
    assert rewriter.resolve("http://localhost:5173/a?b=1#c") == "https://staging.test:8443/a?b=1#c"
    assert rewriter.resolve("http://cdn.other/x") == "http://cdn.other/x"
