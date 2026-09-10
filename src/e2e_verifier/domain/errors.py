from __future__ import annotations


class VerifierError(Exception):
    pass


class HostNotAllowedError(VerifierError):
    def __init__(self, url: str) -> None:
        super().__init__(f"Host of URL is not on the allowlist: {url}")
        self.url = url


class InvalidRunIdError(VerifierError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Invalid run_id: {run_id!r}")
        self.run_id = run_id


class RunNotFoundError(VerifierError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run not found: {run_id}")
        self.run_id = run_id


class RunInProgressError(VerifierError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run is still in progress: {run_id}")
        self.run_id = run_id


class ArtifactNotFoundError(VerifierError):
    def __init__(self, run_id: str, name: str) -> None:
        super().__init__(f"Artifact {name!r} does not exist for run {run_id}")
        self.run_id = run_id
        self.name = name


class FixturePathError(VerifierError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Path is not inside E2E_FIXTURE_DIR: {path}")
        self.path = path


class PlanError(VerifierError):
    def __init__(self, messages: list[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages


class BrowserUnavailableError(VerifierError):
    pass


class SessionNotFoundError(VerifierError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"No open interactive session with id {session_id}")
        self.session_id = session_id


class TooManySessionsError(VerifierError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Limit of {limit} open interactive sessions reached; close one with session_close"
        )
        self.limit = limit
