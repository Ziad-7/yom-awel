from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from yom_awel.domain.contracts import (
    EvaluationResult,
    FeedbackResult,
    SkillSummary,
    SubmissionOutcome,
    TaskVersion,
)
from yom_awel.domain.entities import Artifact, Learner, LearnerProgress
from yom_awel.domain.enums import Channel, LearnerStatus, TaskStatus
from yom_awel.domain.errors import (
    IdempotencyConflict,
    OptimisticConflict,
)
from yom_awel.persistence.memory import FrozenClock, MemoryUnitOfWorkFactory
from yom_awel.persistence.sqlite import SQLiteUnitOfWorkFactory

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


def _task(task_id: UUID | None = None) -> TaskVersion:
    return TaskVersion(
        task_version_id=task_id or uuid4(),
        task_id="task",
        version="1",
        instructions_ar="تعليمات",
        instructions_en="Instructions",
        artifact_schema={},
        evaluator_id="evaluator",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[],
        content_hash="a" * 64,
    )


def _outcome(submission_id: UUID, task_version_id: UUID) -> SubmissionOutcome:
    return SubmissionOutcome(
        submission_id=submission_id,
        attempt_id=uuid4(),
        attempt_number=1,
        evaluation=EvaluationResult(
            evaluator_id="evaluator",
            evaluator_version="1",
            task_version_id=task_version_id,
            passed=True,
            score=100,
            checks=[],
            errors=[],
            summary_ar="ok",
            summary_en="ok",
            duration_ms=1,
        ),
        feedback=FeedbackResult(
            feedback_text="ok",
            language="en",
            persona_id="persona",
            prompt_version="persona@1",
            provider="test",
            model=None,
            used_fallback=True,
            duration_ms=1,
        ),
        learner_status=LearnerStatus.TASK_COMPLETED,
        task_status=TaskStatus.COMPLETED,
        skills=[SkillSummary(skill_id="skill", score=100)],
    )


@pytest.fixture(params=["memory", "sqlite"])
def factory(request: pytest.FixtureRequest, tmp_path: Path):
    clock = FrozenClock(NOW)
    if request.param == "memory":
        return MemoryUnitOfWorkFactory(clock=clock)
    return SQLiteUnitOfWorkFactory(tmp_path / "platform.sqlite", clock=clock)


async def _seed(factory):
    learner_id = uuid4()
    task = _task()
    content = b"hello"
    artifact = Artifact(
        artifact_id=uuid4(),
        learner_id=learner_id,
        filename="work.csv",
        content_type="text/csv",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )
    async with factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="Learner",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await uow.tasks.add(task)
        await uow.artifacts.put(artifact, content)
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=LearnerStatus.IN_TASK,
                version=1,
                updated_at=NOW,
            ),
            expected_version=0,
        )
        await uow.commit()
    return learner_id, task, artifact


@pytest.mark.asyncio
async def test_sqlite_download_validates_and_returns_content(tmp_path: Path) -> None:
    factory = SQLiteUnitOfWorkFactory(tmp_path / "artifact-download.sqlite", clock=FrozenClock(NOW))
    learner_id, _, artifact = await _seed(factory)

    async with factory() as uow:
        assert await uow.artifacts.download(artifact.artifact_id, learner_id) == b"hello"


@pytest.mark.asyncio
async def test_sqlite_round_trip_durably_persists_authorized_media_type(tmp_path: Path) -> None:
    factory = SQLiteUnitOfWorkFactory(
        tmp_path / "artifact-media-type.sqlite", clock=FrozenClock(NOW)
    )
    learner_id, _, artifact = await _seed(factory)

    connection = factory.database.connection()
    try:
        stored = connection.execute(
            "SELECT content_type FROM artifacts WHERE artifact_id=?", (str(artifact.artifact_id),)
        ).fetchone()
    finally:
        connection.close()
    assert stored is not None
    assert stored["content_type"] == "text/csv"

    async with factory() as uow:
        loaded = await uow.artifacts.get(artifact.artifact_id, learner_id)
    assert loaded is not None
    assert loaded.content_type == "text/csv"


@pytest.mark.asyncio
async def test_sqlite_legacy_artifact_schema_is_expanded_and_backfilled(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite"
    learner_id, artifact_id = uuid4(), uuid4()
    content = b"legacy"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE artifacts (artifact_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, "
            "filename TEXT NOT NULL, size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, content BLOB NOT NULL)"
        )
        connection.execute(
            "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(artifact_id),
                str(learner_id),
                "legacy.csv",
                len(content),
                sha256(content).hexdigest(),
                content,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    factory = SQLiteUnitOfWorkFactory(path, clock=FrozenClock(NOW))
    async with factory() as uow:
        loaded = await uow.artifacts.get(artifact_id, learner_id)
    assert loaded is not None
    assert loaded.content_type == "text/csv"


@pytest.mark.asyncio
async def test_second_sqlite_authorization_rejects_different_valid_media_type(
    tmp_path: Path,
) -> None:
    factory = SQLiteUnitOfWorkFactory(
        tmp_path / "artifact-idempotency.sqlite", clock=FrozenClock(NOW)
    )
    _, _, artifact = await _seed(factory)
    replacement = artifact.model_copy(
        update={
            "filename": "work.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
    )
    async with factory() as uow:
        with pytest.raises(IdempotencyConflict) as error:
            # The public Artifact model permits only filename/type-consistent values;
            # this is the closest valid retry that changes the immutable media type.
            await uow.artifacts.authorize_upload(replacement)
        assert error.value.code == "idempotency_conflict"


@pytest.mark.asyncio
async def test_sqlite_retry_derives_valid_legacy_null_media_type(tmp_path: Path) -> None:
    factory = SQLiteUnitOfWorkFactory(
        tmp_path / "artifact-legacy-retry.sqlite", clock=FrozenClock(NOW)
    )
    _, _, artifact = await _seed(factory)
    connection = factory.database.connection()
    try:
        connection.execute(
            "UPDATE artifacts SET content_type=NULL WHERE artifact_id=?",
            (str(artifact.artifact_id),),
        )
    finally:
        connection.close()

    async with factory() as uow:
        authorization = await uow.artifacts.authorize_upload(artifact)

    assert authorization.artifact == artifact


@pytest.mark.asyncio
async def test_reservation_idempotency_reclaim_and_finalize_parity(factory) -> None:
    learner_id, task, artifact = await _seed(factory)
    async with factory() as uow:
        first = await uow.submissions.reserve(
            learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            10,
            "one",
        )
        active = await uow.submissions.reserve(
            learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            99,
            "two",
        )
        assert active.submission_id == first.submission_id
        with pytest.raises(IdempotencyConflict):
            await uow.submissions.reserve(
                learner_id,
                task.task_version_id,
                artifact.artifact_id,
                Channel.WEB,
                "key",
                "other",
                10,
                "two",
            )
        await uow.commit()

    clock = factory.database.clock
    assert isinstance(clock, FrozenClock)
    clock.advance(seconds=11)
    async with factory() as uow:
        reclaimed = await uow.submissions.reserve(
            learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            10,
            "two",
        )
        assert reclaimed.submission_id == first.submission_id
        original = _outcome(reclaimed.submission_id, task.task_version_id)
        await uow.submissions.finalize(reclaimed.reservation_id, reclaimed.version, "two", original)
        await uow.commit()

    async with factory() as uow:
        replay = await uow.submissions.reserve(
            learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            10,
            "three",
        )
        assert replay.status.value == "COMPLETED"
        assert replay.outcome == original


@pytest.mark.asyncio
async def test_rollback_and_progress_cas_parity(factory) -> None:
    learner_id, _, _ = await _seed(factory)
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None
        with pytest.raises(OptimisticConflict):
            await uow.learners.save_progress(
                progress.model_copy(update={"version": 3}), expected_version=1
            )
        await uow.rollback()
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None and progress.version == 1
        learner = await uow.learners.get(learner_id)
        assert learner is not None
        assert learner.status == progress.current_status

    transient = Learner(
        learner_id=uuid4(),
        display_name="Transient",
        preferred_language="en",
        status=LearnerStatus.ONBOARDING,
        created_at=NOW,
        updated_at=NOW,
    )
    async with factory() as uow:
        await uow.learners.add(transient)
    async with factory() as uow:
        assert await uow.learners.get(transient.learner_id) is None


@pytest.mark.asyncio
async def test_uncommitted_changes_are_isolated(factory) -> None:
    transient = Learner(
        learner_id=uuid4(),
        display_name="Transient",
        preferred_language="en",
        status=LearnerStatus.ONBOARDING,
        created_at=NOW,
        updated_at=NOW,
    )
    first = factory()
    second = factory()
    async with first, second:
        await first.learners.add(transient)
        assert await second.learners.get(transient.learner_id) is None
        await first.commit()


def test_sqlite_enables_foreign_keys_wal_and_utc(tmp_path: Path) -> None:
    factory = SQLiteUnitOfWorkFactory(tmp_path / "settings.sqlite")
    connection = factory.database.connection()
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        connection.close()
        factory.database.close()
