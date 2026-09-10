from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ulid import ULID

from e2e_verifier.application.store import ArtifactNames, ArtifactStore, RetentionPolicy
from e2e_verifier.domain.enums import ArtifactKind
from e2e_verifier.domain.errors import ArtifactNotFoundError, InvalidRunIdError, RunNotFoundError
from e2e_verifier.domain.result import RunResult


class FrozenClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def monotonic_ms(self) -> int:
        return 0

    def epoch_ms(self) -> int:
        return int(self._now.timestamp() * 1000)


def test_create_run_makes_sortable_ids_and_screenshot_dir(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    first = store.create_run()
    second = store.create_run()
    assert (first.path / ArtifactNames.SCREENSHOTS).is_dir()
    assert store.list_run_ids() == sorted([first.run_id, second.run_id], reverse=True)
    assert not store.is_complete(first.run_id)


@pytest.mark.parametrize("bad", ["../x", "abc", "01J9X0Q3M6WZ2M8Y4K7P1R5T9I", ""])
def test_invalid_run_ids_are_rejected_before_touching_disk(tmp_path: Path, bad: str) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(InvalidRunIdError):
        store.run_dir(bad)


def test_missing_run_raises(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    with pytest.raises(RunNotFoundError):
        store.run_dir(str(ULID()))


def test_result_is_written_atomically_and_read_back(
    tmp_path: Path, sample_result: RunResult
) -> None:
    store = ArtifactStore(tmp_path)
    location = store.create_run()
    result = sample_result.model_copy(update={"run_id": location.run_id})
    store.write_result(location.path, result)
    assert not (location.path / "result.json.tmp").exists()
    assert store.is_complete(location.run_id)
    assert store.read_result(location.run_id).verdict == result.verdict
    assert store.artifact_path(location.run_id, ArtifactKind.RESULT).name == "result.json"


def test_screenshot_lookup_by_index(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    location = store.create_run()
    folder = location.path / ArtifactNames.SCREENSHOTS
    (folder / "002_failed.png").write_bytes(b"b")
    (folder / "001_passed.png").write_bytes(b"a")
    assert store.artifact_path(location.run_id, ArtifactKind.SCREENSHOT, 0).name == "001_passed.png"
    with pytest.raises(ArtifactNotFoundError):
        store.artifact_path(location.run_id, ArtifactKind.SCREENSHOT, 5)
    with pytest.raises(ArtifactNotFoundError):
        store.artifact_path(location.run_id, ArtifactKind.VIDEO)


def test_retention_deletes_by_count_and_age(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    old_id = str(ULID.from_datetime(now - timedelta(days=30)))
    (store.runs_root / old_id / ArtifactNames.SCREENSHOTS).mkdir(parents=True)
    fresh = [store.create_run().run_id for _ in range(4)]
    policy = RetentionPolicy(max_runs=2, max_age_hours=24 * 7, clock=FrozenClock(now))
    deleted = policy.apply(store, protected={fresh[0]})
    assert old_id in deleted
    remaining = store.list_run_ids()
    assert fresh[0] in remaining
    assert len(remaining) == 3
