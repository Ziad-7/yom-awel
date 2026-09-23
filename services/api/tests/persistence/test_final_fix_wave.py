from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from yom_awel.domain.contracts import (
    EvaluationResult,
    FeedbackResult,
    SubmissionOutcome,
    TaskVersion,
)
from yom_awel.domain.entities import Artifact, Learner, LearnerProgress
from yom_awel.domain.enums import Channel, LearnerStatus, TaskStatus
from yom_awel.domain.errors import (
    ArtifactIntegrityFailure,
    ArtifactNotReady,
    IdempotencyConflict,
    LearnerNotEligible,
    OptimisticConflict,
    TaskNotCurrent,
)
from yom_awel.persistence.memory import MemoryUnitOfWorkFactory
from yom_awel.persistence.sqlite import SQLiteUnitOfWorkFactory
from yom_awel.persistence.supabase import SupabaseSubmissionRepository

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def test_forward_reservation_migration_replays_before_progress_gate() -> None:
    root = Path(__file__).resolve().parents[4]
    sql = (root / "supabase/migrations/20260923170000_reservation_replay_order.sql").read_text(
        encoding="utf-8"
    )

    existing_lookup = sql.index(
        "from public.submissions\n"
        "    where learner_id = p_learner_id and idempotency_key = p_idempotency_key\n"
        "    for update;"
    )
    completed_replay = sql.index("if current_row.status = 'COMPLETED'")
    progress_gate = sql.index(
        "if progress_row.current_status not in ('IN_TASK', 'PROCESSING', 'NEEDS_RETRY')"
    )

    assert existing_lookup < completed_replay < progress_gate
    assert "raise exception 'idempotency fingerprint conflict'" in sql[:progress_gate]


def _task(task_version_id: UUID) -> TaskVersion:
    return TaskVersion(
        task_version_id=task_version_id,
        task_id="final-fix-task",
        version="1",
        instructions_ar="تعليمات",
        instructions_en="Instructions",
        artifact_schema={},
        evaluator_id="evaluator",
        evaluator_version="1",
        pass_threshold=50,
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
            persona_id="tarek",
            prompt_version="tarek-feedback@1",
            provider="test",
            model=None,
            used_fallback=True,
            duration_ms=1,
        ),
        learner_status=LearnerStatus.TASK_COMPLETED,
        task_status=TaskStatus.COMPLETED,
        skills=[],
    )


@pytest.mark.asyncio
async def test_sqlite_same_key_concurrent_reservation_replays_winner(tmp_path: Path) -> None:
    factory = SQLiteUnitOfWorkFactory(tmp_path / "concurrent.sqlite")
    learner_id, task_id, artifact_id = uuid4(), uuid4(), uuid4()
    content = b"answer"
    import hashlib

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
        await uow.tasks.add(_task(task_id))
        await uow.artifacts.put(
            Artifact(
                artifact_id=artifact_id,
                learner_id=learner_id,
                filename="answer.txt",
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            ),
            content,
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=LearnerStatus.IN_TASK,
                current_task_id="final-fix-task",
                version=1,
                updated_at=NOW,
            ),
            expected_version=0,
        )
        await uow.commit()

    async def reserve(owner: str):
        async with factory() as uow:
            result = await uow.submissions.reserve(
                learner_id,
                task_id,
                artifact_id,
                Channel.WEB,
                "same-key",
                "b" * 64,
                60,
                owner,
            )
            await uow.commit()
            return result

    first, second = await asyncio.gather(reserve("one"), reserve("two"))
    assert first.submission_id == second.submission_id

    async with factory() as uow:
        assert await uow.submissions.get_reservation(learner_id, "same-key") is not None


@pytest.mark.asyncio
async def test_supabase_unique_race_reloads_same_fingerprint_and_conflicts_on_mismatch() -> None:
    from dataclasses import dataclass

    @dataclass
    class Response:
        data: object
        error: object | None = None

    learner_id = uuid4()
    row = {
        "reservation_id": str(uuid4()),
        "submission_id": str(uuid4()),
        "learner_id": str(learner_id),
        "task_version_id": str(uuid4()),
        "artifact_id": str(uuid4()),
        "channel": "web",
        "idempotency_key": "same-key",
        "request_fingerprint": "c" * 64,
        "status": "RECEIVED",
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        "version": 1,
        "lease_expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "lease_owner": "winner",
        "outcome": None,
    }

    class Rpc:
        async def rpc(self, function: str, params: dict[str, object]) -> Response:
            return Response(None, {"code": "23505"})

    class Query:
        async def select_one(self, table: str, filters: dict[str, object]):
            return row

    repository = SupabaseSubmissionRepository(Rpc(), Query())
    replay = await repository.reserve(
        learner_id,
        UUID(str(row["task_version_id"])),
        UUID(str(row["artifact_id"])),
        Channel.WEB,
        "same-key",
        "c" * 64,
        60,
        "loser",
    )
    assert replay.submission_id == UUID(str(row["submission_id"]))

    with pytest.raises(IdempotencyConflict):
        await repository.reserve(
            learner_id,
            UUID(str(row["task_version_id"])),
            UUID(str(row["artifact_id"])),
            Channel.WEB,
            "same-key",
            "d" * 64,
            60,
            "loser",
        )


@pytest.mark.asyncio
async def test_supabase_finalize_cas_is_shared_domain_conflict() -> None:
    from dataclasses import dataclass

    @dataclass
    class Response:
        data: object
        error: object | None = None

    class Rpc:
        async def rpc(self, function: str, params: dict[str, object]) -> Response:
            return Response(None, {"code": "40001"})

    repository = SupabaseSubmissionRepository(Rpc())
    with pytest.raises(OptimisticConflict):
        await repository.reserve(
            uuid4(), uuid4(), uuid4(), Channel.WEB, "key", "e" * 64, 60, "worker"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("submission task is not learner current task", TaskNotCurrent),
        ("learner is not eligible for task submission", LearnerNotEligible),
    ],
)
async def test_supabase_reserve_maps_task_state_errors_to_domain_validation(
    message: str, expected: type[Exception]
) -> None:
    from dataclasses import dataclass

    @dataclass
    class Response:
        data: object
        error: object | None = None

    class Rpc:
        async def rpc(self, function: str, params: dict[str, object]) -> Response:
            return Response(None, {"code": "22023", "message": message})

    repository = SupabaseSubmissionRepository(Rpc())
    with pytest.raises(expected):
        await repository.reserve(
            uuid4(), uuid4(), uuid4(), Channel.WEB, "key", "e" * 64, 60, "worker"
        )


@pytest.mark.asyncio
async def test_memory_upload_must_be_complete_before_artifact_is_visible() -> None:
    factory = MemoryUnitOfWorkFactory()
    learner_id, artifact_id = uuid4(), uuid4()
    content = b"browser upload"
    import hashlib

    artifact = Artifact(
        artifact_id=artifact_id,
        learner_id=learner_id,
        filename="upload.txt",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
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
        await uow.artifacts.authorize_upload(artifact)
        await uow.commit()

    async with factory() as uow:
        assert await uow.artifacts.get(artifact_id, learner_id) is None
        with pytest.raises(ArtifactNotReady):
            await uow.artifacts.complete_upload(artifact_id, learner_id)
        await uow.artifacts.put(artifact, content)
        await uow.commit()

    async with factory() as uow:
        assert await uow.artifacts.complete_upload(artifact_id, learner_id) == artifact
        assert await uow.artifacts.get(artifact_id, learner_id) == artifact

    other_factory = MemoryUnitOfWorkFactory()
    async with other_factory() as uow:
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
        await uow.artifacts.authorize_upload(artifact)
        assert uow._snapshot is not None
        uow._snapshot.artifacts[artifact_id].content = b"tampered"
        await uow.commit()
    async with other_factory() as uow:
        with pytest.raises(ArtifactIntegrityFailure):
            await uow.artifacts.complete_upload(artifact_id, learner_id)
