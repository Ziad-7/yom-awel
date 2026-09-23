import hashlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from yom_awel.application.commands import ProcessSubmissionCommand
from yom_awel.application.models import ProcessingState
from yom_awel.domain.contracts import (
    ArtifactRef,
    FeedbackResult,
    SubmissionOutcome,
)
from yom_awel.domain.entities import (
    Attempt,
    EvaluationRecord,
    FeedbackRecord,
    OutboxEvent,
    aggregate_skill_evidence,
    extract_skill_evidence,
)
from yom_awel.domain.enums import (
    ErrorCategory,
    Language,
    LearnerStatus,
    SubmissionStatus,
    TaskStatus,
)
from yom_awel.domain.errors import (
    DomainError,
    FinalizationConflict,
    IdempotencyConflict,
    OptimisticConflict,
    ReservationExpired,
    ReservationOwnerConflict,
    SubmissionMismatch,
)
from yom_awel.ports.clock import Clock
from yom_awel.ports.evaluation import Evaluator
from yom_awel.ports.feedback import FeedbackProvider
from yom_awel.ports.id_generator import IDGenerator
from yom_awel.ports.unit_of_work import UnitOfWorkFactory

logger = logging.getLogger(__name__)


def generate_fingerprint(command: ProcessSubmissionCommand) -> str:
    raw = f"{command.learner_id}:{command.task_version_id}:{command.artifact_id}:{command.artifact_sha256}:{command.channel.value}:{command.channel_event_id or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_canonical_fallback(language: str) -> FeedbackResult:
    if language == "ar-EG":
        text = "عذراً، لم نتمكن من تقديم تقييم مخصص في الوقت الحالي. يرجى مراجعة إرشادات المهمة."
    else:
        text = "Sorry, we could not provide custom feedback at this time. Please review the task instructions."

    return FeedbackResult(
        feedback_text=text,
        language=cast(Literal["ar-EG", "en"], language),
        persona_id="eng-tarek",
        prompt_version="tarek-feedback@1",
        provider="deterministic",
        model=None,
        used_fallback=True,
        duration_ms=0,
    )


async def _expire_reservation(
    uow_factory: UnitOfWorkFactory,
    learner_id: UUID,
    idempotency_key: str,
    expected_version: int,
    lease_owner: str,
) -> None:
    """Release only the reservation lease owned by this processing attempt.

    A slow evaluator may finish after another worker reclaimed the lease. In
    that case expiration must be a no-op for the stale worker rather than
    invalidating the newer worker's reservation.
    """

    try:
        async with uow_factory() as uow:
            await uow.submissions.expire(
                learner_id,
                idempotency_key,
                expected_version=expected_version,
                lease_owner=lease_owner,
            )
            await uow.commit()
    except (OptimisticConflict, ReservationOwnerConflict):
        return


class ProcessSubmission:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        evaluator: Evaluator,
        feedback: FeedbackProvider,
        clock: Clock,
        id_gen: IDGenerator,
        post_commit_cleanup: Callable[[datetime], Awaitable[None]] | None = None,
    ):
        self.uow_factory = uow_factory
        self.evaluator = evaluator
        self.feedback = feedback
        self.clock = clock
        self.id_gen = id_gen
        self.post_commit_cleanup = post_commit_cleanup

    async def execute(
        self, command: ProcessSubmissionCommand, lease_owner: str
    ) -> SubmissionOutcome | ProcessingState:
        fingerprint = generate_fingerprint(command)
        res = None
        lang = "en"
        artifact_filename = ""
        artifact_size = 0

        try:
            async with self.uow_factory() as uow:
                learner = await uow.learners.get(command.learner_id)
                if not learner:
                    raise DomainError(
                        "learner_not_found",
                        "Learner not found",
                        category=ErrorCategory.VALIDATION,
                        retryable=False,
                    )

                lang = learner.preferred_language.value

                task_version = await uow.tasks.get(command.task_version_id)
                if not task_version:
                    raise DomainError(
                        "task_not_found",
                        "Task not found",
                        category=ErrorCategory.VALIDATION,
                        retryable=False,
                    )

                artifact = await uow.artifacts.get(command.artifact_id, command.learner_id)
                if not artifact:
                    raise DomainError(
                        "artifact_not_found",
                        "Artifact not found",
                        category=ErrorCategory.VALIDATION,
                        retryable=False,
                    )
                if artifact.sha256 != command.artifact_sha256:
                    raise DomainError(
                        "artifact_hash_mismatch",
                        "Artifact hash mismatch",
                        category=ErrorCategory.VALIDATION,
                        retryable=False,
                    )

                artifact_filename = artifact.filename
                artifact_size = artifact.size_bytes

                res = await uow.submissions.reserve(
                    learner_id=command.learner_id,
                    task_version_id=command.task_version_id,
                    artifact_id=command.artifact_id,
                    channel=command.channel,
                    key=command.idempotency_key,
                    request_fingerprint=fingerprint,
                    lease_seconds=300,
                    lease_owner=lease_owner,
                )

                await uow.commit()
        except OptimisticConflict:
            async with self.uow_factory() as uow_retry:
                res = await uow_retry.submissions.get_reservation(
                    command.learner_id, command.idempotency_key
                )
                if not res:
                    raise DomainError(
                        "reservation_conflict",
                        "Reservation state conflict",
                        category=ErrorCategory.PERSISTENCE,
                        retryable=True,
                    )
                if res.request_fingerprint != fingerprint:
                    raise IdempotencyConflict(command.idempotency_key)

        if res.status == SubmissionStatus.COMPLETED and res.outcome:
            return res.outcome

        if res.lease_owner != lease_owner:
            return ProcessingState(submission_id=res.submission_id, status=res.status)

        artifact_ref = ArtifactRef(
            artifact_id=command.artifact_id,
            filename=artifact_filename,
            size_bytes=artifact_size,
            sha256=command.artifact_sha256,
        )

        # Fetch task_version again since it was in UoW
        async with self.uow_factory() as tmp_uow:
            task_version = await tmp_uow.tasks.get(command.task_version_id)
            if not task_version:
                raise RuntimeError("Task vanished")

        try:
            eval_result = await self.evaluator.evaluate(task_version, artifact_ref)
        except Exception as e:  # noqa: BLE001
            # Expire lock on evaluation failure
            await _expire_reservation(
                self.uow_factory,
                command.learner_id,
                command.idempotency_key,
                res.version,
                lease_owner,
            )
            raise DomainError(
                code="evaluation_failed",
                message=str(e),
                category=ErrorCategory.EVALUATION,
                retryable=True,
            )

        if (
            eval_result.task_version_id != task_version.task_version_id
            or eval_result.evaluator_id != task_version.evaluator_id
            or eval_result.evaluator_version != task_version.evaluator_version
        ):
            await _expire_reservation(
                self.uow_factory,
                command.learner_id,
                command.idempotency_key,
                res.version,
                lease_owner,
            )
            raise DomainError(
                "invalid_evaluator",
                "Evaluator mismatch",
                category=ErrorCategory.EVALUATION,
                retryable=False,
            )

        try:
            feedback_result = await self.feedback.generate(
                eval_result, language=Language(lang), learner_note=command.learner_note
            )
        except Exception:  # noqa: BLE001
            feedback_result = _generate_canonical_fallback(lang)

        attempt_id = self.id_gen.generate()
        eval_id = self.id_gen.generate()
        fb_id = self.id_gen.generate()
        now = self.clock.now()

        try:
            async with self.uow_factory() as uow_fin:
                eval_record = EvaluationRecord(
                    evaluation_id=eval_id, result=eval_result, recorded_at=now
                )
                await uow_fin.evaluations.add(eval_record)

                fb_record = FeedbackRecord(
                    feedback_id=fb_id, result=feedback_result, recorded_at=now
                )
                await uow_fin.feedback.add(fb_record)

                attempts = await uow_fin.attempts.list_for_task(
                    command.learner_id, command.task_version_id
                )
                attempt_num = len(attempts) + 1

                attempt = Attempt(
                    attempt_id=attempt_id,
                    learner_id=command.learner_id,
                    submission_id=res.submission_id,
                    task_version_id=command.task_version_id,
                    attempt_number=attempt_num,
                    evaluation_id=eval_id,
                    feedback_id=fb_id,
                    evaluator_id=eval_result.evaluator_id,
                    evaluator_version=eval_result.evaluator_version,
                    prompt_version=feedback_result.prompt_version,
                    started_at=getattr(res, "created_at", now),
                    completed_at=now,
                )
                await uow_fin.attempts.add(attempt)

                extracted = extract_skill_evidence(
                    command.learner_id, attempt_id, task_version, eval_result, now
                )
                if eval_result.passed:
                    for ev in extracted:
                        new_ev = ev.model_copy(update={"evidence_id": self.id_gen.generate()})
                        await uow_fin.skills.add_evidence(new_ev)

                curr_progress = await uow_fin.learners.get_progress(command.learner_id)
                if not curr_progress:
                    raise DomainError(
                        "progress_not_found",
                        "Progress not found",
                        category=ErrorCategory.VALIDATION,
                        retryable=False,
                    )

                from yom_awel.domain.state_machine import evaluate_transition, transition

                # External work happens before this transaction. Validate the
                # normal processing hop in memory, then persist only the
                # terminal result once; failed external work leaves progress
                # untouched and a competing finalizer loses the progress CAS.
                processing_status = curr_progress.current_status
                if processing_status in (LearnerStatus.IN_TASK, LearnerStatus.NEEDS_RETRY):
                    processing_status = transition(processing_status, LearnerStatus.PROCESSING)
                new_status = evaluate_transition(processing_status, eval_result, False)
                new_progress = curr_progress.model_copy(
                    update={
                        "current_status": new_status,
                        "version": curr_progress.version + 1,
                        "updated_at": now,
                    }
                )
                await uow_fin.learners.save_progress(
                    new_progress, expected_version=curr_progress.version
                )

                await uow_fin.outbox.add(
                    OutboxEvent(
                        event_id=self.id_gen.generate(),
                        event_type="submission.processed",
                        aggregate_id=command.learner_id,
                        payload={
                            "submission_id": str(res.submission_id),
                            "passed": eval_result.passed,
                        },
                        created_at=now,
                    )
                )

                skills_list = await uow_fin.skills.list_evidence(command.learner_id)
                aggregated = aggregate_skill_evidence(skills_list)

                t_status = TaskStatus.COMPLETED if eval_result.passed else TaskStatus.ACTIVE

                outcome = SubmissionOutcome(
                    submission_id=res.submission_id,
                    attempt_id=attempt_id,
                    attempt_number=attempt_num,
                    evaluation=eval_result,
                    feedback=feedback_result,
                    learner_status=new_progress.current_status,
                    task_status=t_status,
                    skills=aggregated,
                )

                await uow_fin.submissions.finalize(
                    reservation_id=res.reservation_id,
                    expected_version=res.version,
                    lease_owner=lease_owner,
                    outcome=outcome,
                )
                await uow_fin.commit()
                # The submission is accepted once its transaction commits.
                # Retention is bounded opportunistic maintenance and must
                # never turn a successful submission into a failed request.
                if self.post_commit_cleanup is not None:
                    try:
                        await self.post_commit_cleanup(now)
                    except Exception as error:  # noqa: BLE001
                        # Log only the exception type: provider messages may
                        # contain sensitive infrastructure details.
                        logger.warning(
                            "post_commit_retention_cleanup_failed: %s", type(error).__name__
                        )
                return outcome

        except (
            OptimisticConflict,
            FinalizationConflict,
            ReservationExpired,
            ReservationOwnerConflict,
            SubmissionMismatch,
        ):
            raise DomainError(
                code="finalization_conflict",
                message="Finalization conflicted",
                category=ErrorCategory.PERSISTENCE,
                retryable=True,
            )
