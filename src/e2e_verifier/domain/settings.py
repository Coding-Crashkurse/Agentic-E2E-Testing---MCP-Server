from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from e2e_verifier.domain.options import HudLanguage
from e2e_verifier.domain.ticket import BrowserName

DEFAULT_ALLOWED_HOSTS = ("localhost", "127.0.0.1", "[::1]")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="E2E_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    artifact_dir: Path = Path("artifacts")
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_HOSTS)
    )
    allow_any_host: bool = False
    browser: BrowserName = "chromium"
    headless: bool = True
    default_step_timeout_ms: int = Field(default=10_000, ge=100, le=120_000)
    default_run_timeout_s: int = Field(default=120, ge=5)
    max_run_timeout_s: int = Field(default=600, ge=5)
    max_parallel_runs: int = Field(default=1, ge=1, le=8)
    max_runs_retained: int = Field(default=50, ge=1)
    max_artifact_age_h: int = Field(default=168, ge=1)
    max_inline_artifact_mb: int = Field(default=8, ge=1)
    max_log_entries: int = Field(default=10_000, ge=100)
    fixture_dir: Path | None = None
    ffmpeg_path: Path | None = None
    transport: Literal["stdio", "http"] = "stdio"
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8765, ge=1, le=65_535)
    allow_remote_bind: bool = False
    log_level: str = "INFO"
    hud_language: HudLanguage = "en"
    session_close_timeout_s: int = Field(default=20, ge=5)
    max_sessions: int = Field(default=3, ge=1, le=10)
    session_idle_timeout_s: int = Field(default=600, ge=30)
    inline_screenshot_quality: int = Field(default=70, ge=20, le=95)

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @property
    def max_inline_artifact_bytes(self) -> int:
        return self.max_inline_artifact_mb * 1024 * 1024
