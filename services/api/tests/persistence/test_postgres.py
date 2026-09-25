"""Postgres adapter against a real Postgres 16.

Uses POSTGRES_TEST_DSN when set (CI service container); otherwise starts a
throwaway cluster from the local Postgres binaries. Skips cleanly when
neither is available. Every test works in its own schema.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import traceback
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import conninfo, sql

from tests.evaluation.support import PACKAGE, REFERENCE, TASK_VERSION, to_xlsx
from tests.persistence import test_sqlite_contract as parity
from tests.persistence.repository_contract import (
    assert_preferred_language_update,
    assert_progress_rollback_and_cas,
    assert_reservation_and_finalization,
)
from yom_awel.application.commands import CreateUploadCommand, ProcessSubmissionCommand
from yom_awel.application.submissions import ProcessSubmission
from yom_awel.application.tasks import CompleteArtifactUpload, CreateArtifactUpload
from yom_awel.domain.contracts import SubmissionOutcome
from yom_awel.domain.entities import Artifact, Learner, LearnerProgress
from yom_awel.domain.enums import Channel, Language, LearnerStatus
from yom_awel.domain.errors import (
    ArtifactIntegrityFailure,
    ArtifactNotReady,
    LearnerScopeViolation,
    OptimisticConflict,
    UniqueConstraintViolation,
)
from yom_awel.evaluation.clean_sales_dataset import to_csv
from yom_awel.evaluation.sales_cleaning import SalesCleaningEvaluator
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.persistence.memory import FrozenClock
from yom_awel.persistence.postgres import PersistenceUnavailable, PostgresUnitOfWorkFactory

REPO_ROOT = Path(__file__).resolve().parents[4]
DIRTY_CSV = REPO_ROOT / "task_packages" / "clean-sales" / "1" / "data" / "sales_dirty.csv"
DEPLOY_DOC = REPO_ROOT / "docs" / "operations" / "deploy.md"
POSTGRES_BIN = Path(os.environ.get("POSTGRES_BIN", "/usr/lib/postgresql/16/bin"))
NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _cluster_owner() -> list[str]:
    """initdb refuses to run as root, so run the cluster as the postgres user."""

    if os.name == "nt" or os.geteuid() != 0:
        return []
    import pwd

    try:
        pwd.getpwnam("postgres")
    except KeyError:
        pytest.skip("running as root without a postgres user to own the test cluster")
    return ["runuser", "-u", "postgres", "--"]


@pytest.fixture(scope="session")
def postgres_dsn() -> Iterator[str]:
    configured = os.environ.get("POSTGRES_TEST_DSN")
    if configured:
        yield configured
        return
    if not (POSTGRES_BIN / "initdb").is_file():
        pytest.skip("set POSTGRES_TEST_DSN or install Postgres 16 binaries")
    owner = _cluster_owner()
    root = Path(tempfile.mkdtemp(prefix="yom-awel-pg-"))
    if owner:
        shutil.chown(root, user="postgres")
    data, port = root / "data", _free_port()
    subprocess.run(
        [*owner, str(POSTGRES_BIN / "initdb"), "-D", str(data), "-U", "postgres"]
        + ["--auth=trust", "--encoding=UTF8", "--no-sync"],
        check=True,
        capture_output=True,
    )
    pg_ctl = [*owner, str(POSTGRES_BIN / "pg_ctl"), "-D", str(data)]
    subprocess.run(
        [*pg_ctl, "-l", str(root / "server.log"), "-w", "start", "-o"]
        + [f"-p {port} -k {root} -c listen_addresses=127.0.0.1 -c fsync=off"],
        check=True,
        capture_output=True,
    )
    try:
        yield f"postgresql://postgres@127.0.0.1:{port}/postgres?sslmode=disable"
    finally:
        subprocess.run([*pg_ctl, "-m", "immediate", "-w", "stop"], check=True, capture_output=True)
        shutil.rmtree(root, ignore_errors=True)


def _schema() -> str:
    return f"t_{uuid4().hex}"


@pytest.fixture
def factory(postgres_dsn: str) -> PostgresUnitOfWorkFactory:
    return PostgresUnitOfWorkFactory(postgres_dsn, schema=_schema(), clock=FrozenClock(NOW))


# Shared contract and SQLite parity: the same test bodies the other adapters run.


async def test_preferred_language_update(factory: PostgresUnitOfWorkFactory) -> None:
    await assert_preferred_language_update(factory)


async def test_repository_contract_reservation_and_finalization(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    await assert_reservation_and_finalization(factory)


async def test_repository_contract_progress_rollback_and_cas(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    await assert_progress_rollback_and_cas(factory)


async def test_sqlite_parity_reservation_reclaim_and_finalize(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    await parity.test_reservation_idempotency_reclaim_and_finalize_parity(factory)


async def test_sqlite_parity_rollback_and_progress_cas(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    await parity.test_rollback_and_progress_cas_parity(factory)


async def test_sqlite_parity_uncommitted_changes_are_isolated(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    await parity.test_uncommitted_changes_are_isolated(factory)


# Postgres-specific concurrency.


async def _learner_in_task(factory: PostgresUnitOfWorkFactory) -> tuple[UUID, Artifact]:
    learner_id, _, artifact = await parity._seed(factory)
    return learner_id, artifact


async def test_concurrent_same_key_reservations_replay_the_winner(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    learner_id, task, artifact = await parity._seed(factory)

    async def reserve(owner: str) -> UUID:
        async with factory() as uow:
            result = await uow.submissions.reserve(
                learner_id,
                task.task_version_id,
                artifact.artifact_id,
                Channel.WEB,
                "same-key",
                "b" * 64,
                60,
                owner,
            )
            await uow.commit()
            return result.submission_id

    winners = await asyncio.gather(*(reserve(f"worker-{index}") for index in range(5)))
    assert len(set(winners)) == 1


async def test_concurrent_progress_writers_lose_the_compare_and_set(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    learner_id, _ = await _learner_in_task(factory)
    first, second = factory(), factory()
    async with first, second:
        progress = await first.learners.get_progress(learner_id)
        assert progress is not None
        advanced = progress.model_copy(update={"version": 2, "updated_at": NOW})
        await first.learners.save_progress(advanced, expected_version=1)
        blocked = asyncio.create_task(second.learners.save_progress(advanced, expected_version=1))
        await asyncio.sleep(0.2)
        assert not blocked.done(), "second writer must wait on the progress row lock"
        await first.commit()
        with pytest.raises(OptimisticConflict):
            await blocked
    async with factory() as uow:
        stored = await uow.learners.get_progress(learner_id)
        assert stored is not None and stored.version == 2


async def test_writers_for_different_learners_do_not_conflict(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    first_id, _ = await _learner_in_task(factory)
    second_id = await _start_clean_sales(factory, Language.EN)
    first, second = factory(), factory()
    async with first, second:
        for uow, learner_id in ((first, first_id), (second, second_id)):
            progress = await uow.learners.get_progress(learner_id)
            assert progress is not None
            await uow.learners.save_progress(
                progress.model_copy(update={"version": 2}), expected_version=1
            )
        await second.commit()
        await first.commit()


async def test_schema_bootstrap_is_idempotent_under_concurrent_cold_starts(
    postgres_dsn: str,
) -> None:
    schema = _schema()
    factories = [PostgresUnitOfWorkFactory(postgres_dsn, schema=schema) for _ in range(4)]

    async def touch(item: PostgresUnitOfWorkFactory) -> None:
        async with item() as uow:
            assert await uow.learners.get(uuid4()) is None

    await asyncio.gather(*(touch(item) for item in factories))
    await touch(PostgresUnitOfWorkFactory(postgres_dsn, schema=schema))


def test_schema_name_must_be_a_plain_identifier(postgres_dsn: str) -> None:
    for unsafe in ("public; DROP TABLE x", "Yom", "pg_catalog", "", "a" * 64):
        with pytest.raises(ValueError):
            PostgresUnitOfWorkFactory(postgres_dsn, schema=unsafe)


# Artifact bytes in bytea.


def _artifact(learner_id: UUID, content: bytes, filename: str = "sales.csv") -> Artifact:
    return Artifact(
        artifact_id=uuid4(),
        learner_id=learner_id,
        filename=filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


async def test_upload_lifecycle_stores_bytes_and_verifies_integrity(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    learner_id, _ = await _learner_in_task(factory)
    content = b"\x00\xffbinary,\n" * 1000
    artifact = _artifact(learner_id, content, "sales.xlsx")
    async with factory() as uow:
        await uow.artifacts.authorize_upload(artifact)
        await uow.commit()
    async with factory() as uow:
        assert await uow.artifacts.get(artifact.artifact_id, learner_id) is None
        with pytest.raises(ArtifactNotReady):
            await uow.artifacts.complete_upload(artifact.artifact_id, learner_id)
        await uow.artifacts.put(artifact, content)
        assert await uow.artifacts.complete_upload(artifact.artifact_id, learner_id) == artifact
        with pytest.raises(UniqueConstraintViolation):
            await uow.artifacts.put(artifact, content)
        await uow.commit()
    async with factory() as uow:
        assert await uow.artifacts.get(artifact.artifact_id, learner_id) == artifact
        assert await uow.artifacts.download(artifact.artifact_id, learner_id) == content
        assert await uow.artifacts.get(artifact.artifact_id, uuid4()) is None
        with pytest.raises(LearnerScopeViolation):
            await uow.artifacts.delete(artifact.artifact_id, uuid4())
        await uow.artifacts.delete(artifact.artifact_id, learner_id)
        assert await uow.artifacts.download(artifact.artifact_id, learner_id) is None


async def test_tampered_bytes_are_rejected(
    factory: PostgresUnitOfWorkFactory, postgres_dsn: str
) -> None:
    learner_id, artifact = await _learner_in_task(factory)
    with psycopg.connect(postgres_dsn) as admin:
        admin.execute(
            sql.SQL("UPDATE {}.artifacts SET content=%s WHERE artifact_id=%s").format(
                sql.Identifier(factory.database.schema)
            ),
            (b"hellO", artifact.artifact_id),
        )
    async with factory() as uow:
        assert await uow.artifacts.get(artifact.artifact_id, learner_id) is None
        assert await uow.artifacts.download(artifact.artifact_id, learner_id) is None
        with pytest.raises(ArtifactIntegrityFailure):
            await uow.artifacts.complete_upload(artifact.artifact_id, learner_id)


async def test_artifacts_are_capped_at_five_mebibytes(
    factory: PostgresUnitOfWorkFactory, postgres_dsn: str
) -> None:
    learner_id, _ = await _learner_in_task(factory)
    largest = b"x" * (5 * 1024 * 1024)
    artifact = _artifact(learner_id, largest)
    async with factory() as uow:
        await uow.artifacts.put(artifact, largest)
        await uow.commit()
    async with factory() as uow:
        assert await uow.artifacts.download(artifact.artifact_id, learner_id) == largest
    with psycopg.connect(postgres_dsn) as admin, pytest.raises(psycopg.errors.CheckViolation):
        admin.execute(
            sql.SQL("UPDATE {}.artifacts SET content=content || %s WHERE artifact_id=%s").format(
                sql.Identifier(factory.database.schema)
            ),
            (b"x", artifact.artifact_id),
        )


async def test_constraint_violation_keeps_the_transaction_usable(
    factory: PostgresUnitOfWorkFactory,
) -> None:
    learner_id, _ = await _learner_in_task(factory)
    async with factory() as uow:
        learner = await uow.learners.get(learner_id)
        assert learner is not None
        with pytest.raises(UniqueConstraintViolation):
            await uow.learners.add(learner)
        assert await uow.learners.get(learner_id) == learner


# The DSN never leaks.


async def test_unreachable_database_error_carries_no_connection_details() -> None:
    user, password, port = "leak_probe_user", secrets.token_hex(12), _free_port()
    dsn = conninfo.make_conninfo(
        host="127.0.0.1", port=port, user=user, password=password, sslmode="disable"
    )
    factory = PostgresUnitOfWorkFactory(dsn, connect_timeout=1)
    with pytest.raises(PersistenceUnavailable) as raised:
        async with factory():
            pass
    rendered = "".join(traceback.format_exception(raised.value))
    rendered += repr(factory) + repr(factory.database) + repr(raised.value.details)
    for fragment in (password, user, str(port)):
        assert fragment not in rendered
    assert raised.value.code == "unavailable"


# Least privilege: the role SQL in docs/operations/deploy.md really works.


def _documented_role_sql() -> str:
    text = DEPLOY_DOC.read_text(encoding="utf-8")
    match = re.search(r"```sql\n(-- yom_awel least-privilege role\n.*?)```", text, re.DOTALL)
    assert match, "deploy.md must keep the least-privilege role SQL block"
    return match.group(1)


async def test_documented_least_privilege_role_runs_the_adapter(postgres_dsn: str) -> None:
    role, schema, password = f"r_{uuid4().hex[:12]}", _schema(), secrets.token_hex(16)
    script = (
        _documented_role_sql()
        .replace("<strong-password>", password)
        .replace("yom_awel_app", role)
        .replace("yom_awel", schema)
    )
    with psycopg.connect(postgres_dsn, autocommit=True) as admin:
        admin.execute(script.encode())
    app_dsn = conninfo.make_conninfo(postgres_dsn, user=role, password=password)
    factory = PostgresUnitOfWorkFactory(app_dsn, schema=schema, clock=FrozenClock(NOW))
    await assert_reservation_and_finalization(factory)
    with psycopg.connect(app_dsn, autocommit=True) as app:
        for statement in ("CREATE SCHEMA escape_hatch", "CREATE TABLE public.escape (id int)"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                app.execute(statement.encode())
        superuser = app.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        assert superuser.fetchone() == (False,)


# End-to-end slice: ProcessSubmission with the real evaluator and fallback feedback.


class _Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class _IDs:
    def generate(self) -> UUID:
        return uuid4()


async def _start_clean_sales(factory: PostgresUnitOfWorkFactory, language: Language) -> UUID:
    learner_id = uuid4()
    async with factory() as uow:
        if await uow.tasks.get(TASK_VERSION.task_version_id) is None:
            await uow.tasks.add(TASK_VERSION)
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="Salma",
                preferred_language=language,
                status=LearnerStatus.IN_TASK,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=LearnerStatus.IN_TASK,
                current_task_id=TASK_VERSION.task_id,
                version=1,
                updated_at=NOW,
            ),
            expected_version=0,
        )
        await uow.commit()
    return learner_id


async def _submit(
    factory: PostgresUnitOfWorkFactory,
    learner_id: UUID,
    filename: str,
    content: bytes,
    key: str,
) -> SubmissionOutcome:
    clock, ids = _Clock(), _IDs()
    sha256 = hashlib.sha256(content).hexdigest()
    upload = await CreateArtifactUpload(factory, clock, ids).execute(
        CreateUploadCommand(
            learner_id=learner_id,
            filename=filename,
            size_bytes=len(content),
            artifact_sha256=sha256,
        )
    )
    async with factory() as uow:
        await uow.artifacts.put(
            Artifact(
                artifact_id=upload.artifact_id,
                learner_id=learner_id,
                filename=filename,
                size_bytes=len(content),
                sha256=sha256,
            ),
            content,
        )
        await uow.commit()
    await CompleteArtifactUpload(factory).execute(learner_id, upload.artifact_id)
    processor = ProcessSubmission(
        factory, SalesCleaningEvaluator(PACKAGE), DeterministicFeedbackProvider(), clock, ids
    )
    outcome = await processor.execute(
        ProcessSubmissionCommand(
            learner_id=learner_id,
            task_version_id=TASK_VERSION.task_version_id,
            artifact_id=upload.artifact_id,
            artifact_sha256=sha256,
            channel=Channel.WEB,
            idempotency_key=key,
        ),
        lease_owner=f"test-{key}",
    )
    assert isinstance(outcome, SubmissionOutcome)
    return outcome


CHECK_IDS = ["unique_orders", "standard_dates", "valid_numeric_values", "complete_customer_records"]


@pytest.mark.parametrize("language", [Language.AR_EG, Language.EN])
@pytest.mark.parametrize("passing_format", ["csv", "xlsx"])
async def test_process_submission_round_trip(
    factory: PostgresUnitOfWorkFactory, language: Language, passing_format: str
) -> None:
    learner_id = await _start_clean_sales(factory, language)

    failed = await _submit(factory, learner_id, "sales_dirty.csv", DIRTY_CSV.read_bytes(), "one")
    assert [check.check_id for check in failed.evaluation.checks] == CHECK_IDS
    assert not failed.evaluation.passed and failed.evaluation.score < 75
    assert failed.learner_status == LearnerStatus.NEEDS_RETRY
    assert failed.feedback.language == language and failed.feedback.used_fallback
    assert failed.attempt_number == 1

    clean = (
        to_csv(REFERENCE.clean).encode() if passing_format == "csv" else to_xlsx(REFERENCE.clean)
    )
    passed = await _submit(factory, learner_id, f"sales_clean.{passing_format}", clean, "two")
    assert passed.evaluation.passed and passed.evaluation.score == 100
    assert all(check.passed for check in passed.evaluation.checks)
    assert passed.learner_status == LearnerStatus.TASK_COMPLETED
    assert passed.attempt_number == 2
    assert passed.skills

    async with factory() as uow:
        attempts = await uow.attempts.list_for_task(learner_id, TASK_VERSION.task_version_id)
        assert [attempt.submission_id for attempt in attempts] == [
            failed.submission_id,
            passed.submission_id,
        ]
        stored = await uow.evaluations.get(attempts[1].evaluation_id)
        assert stored is not None and stored.result == passed.evaluation
        feedback = await uow.feedback.get(attempts[1].feedback_id)
        assert feedback is not None and feedback.result == passed.feedback
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None and progress.current_status == LearnerStatus.TASK_COMPLETED
        replay = await uow.submissions.get_reservation(learner_id, "two")
        assert replay is not None and replay.outcome == passed
        profile = await uow.skills.get_profile(learner_id)
        assert profile.skills == passed.skills
