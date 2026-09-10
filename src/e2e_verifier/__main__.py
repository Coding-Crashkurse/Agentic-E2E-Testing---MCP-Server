from __future__ import annotations

import logging
import sys

from e2e_verifier.domain.settings import Settings
from e2e_verifier.server.app import ServerFactory

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class Application:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(self) -> None:
        logging.basicConfig(
            level=self._settings.log_level.upper(),
            stream=sys.stderr,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        server = ServerFactory(self._settings).build()
        if self._settings.transport == "http":
            self._check_bind()
            server.run(
                transport="http",
                host=self._settings.http_host,
                port=self._settings.http_port,
            )
            return
        server.run(transport="stdio")

    def _check_bind(self) -> None:
        host = self._settings.http_host.strip("[]").lower()
        if host not in LOCAL_HOSTS and not self._settings.allow_remote_bind:
            raise SystemExit(
                f"Refusing to bind HTTP transport to {self._settings.http_host}; "
                "set E2E_ALLOW_REMOTE_BIND=true to allow it"
            )


def main() -> None:
    Application(Settings()).run()


if __name__ == "__main__":
    main()
