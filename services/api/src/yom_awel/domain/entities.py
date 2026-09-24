from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from yom_awel.domain.contracts import (
    ArtifactContentType,
    EvaluationResult,
    FeedbackResult,
    SkillSummary,
    SubmissionOutcome,
    TaskVersion,
    artifact_content_type,
)
from yom_awel.domain.enums import Channel, Language, LearnerStatus, SubmissionStatus


class Learner(BaseModel):
    learner_id: UUID
    display_name: str = Field(strict=True, min_length=1)
    preferred_language: Language
    status: LearnerStatus
    created_at: datetime
    updated_at: datetime
    state_machine_version: str = Field(default="1", strict=True, min_length=1)
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExternalIdentity(BaseModel):
    identity_id: UUID
    learner_id: UUID
    provider: str = Field(strict=True, min_length=1)
    provider_subject: str = Field(strict=True, min_length=1)
    model_config = ConfigDict(frozen=True, extra="forbid")


class Task(BaseModel):
    task_id: str = Field(strict=True, min_length=1)
    title: str = Field(strict=True, min_length=1)
    model_config = ConfigDict(frozen=True, extra="forbid")


class Artifact(BaseModel):
    artifact_id: UUID
    learner_id: UUID
    filename: str = Field(strict=True, min_length=1, max_length=255)
    content_type: ArtifactContentType
    size_bytes: int = Field(strict=True, ge=0, le=5 * 1024 * 1024)
    sha256: str = Field(strict=True, pattern=r"^[a-f0-9]{64}$")
    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_content_type(self) -> "Artifact":
        if self.content_type != artifact_content_type(self.filename):
            raise ValueError("content_type must match filename")
        return self


class SubmissionReservation(BaseModel):
    reservation_id: UUID
    submission_id: UUID
    learner_id: UUID
    task_version_id: UUID
    artifact_id: UUID | None = None
    channel: Channel | None = None
    idempotency_key: str = Field(strict=True, min_length=1)
    request_fingerprint: str = Field(strict=True, min_length=1)
    status: SubmissionStatus
    created_at: datetime
    version: int = Field(strict=True, ge=1)
    lease_expires_at: datetime
    lease_owner: str | None = None
    outcome: SubmissionOutcome | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class OutboxEvent(BaseModel):
    event_id: UUID
    event_type: str = Field(strict=True, min_length=1)
    aggregate_id: UUID
    payload: dict[str, object]
    created_at: datetime
    published_at: datetime | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationRecord(BaseModel):
    evaluation_id: UUID
    result: EvaluationResult
    recorded_at: datetime
    model_config = ConfigDict(frozen=True, extra="forbid")


class FeedbackRecord(BaseModel):
    feedback_id: UUID
    result: FeedbackResult
    recorded_at: datetime
    model_config = ConfigDict(frozen=True, extra="forbid")


class SkillEvidence(BaseModel):
    evidence_id: UUID
    learner_id: UUID
    attempt_id: UUID
    task_version_id: UUID
    skill_id: str = Field(strict=True, min_length=1)
    check_id: str = Field(strict=True, min_length=1)
    awarded_points: int = Field(strict=True, ge=0)
    available_points: int = Field(strict=True, gt=0)
    recorded_at: datetime
    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_points(self) -> "SkillEvidence":
        if self.awarded_points > self.available_points:
            raise ValueError("awarded_points cannot exceed available_points")
        return self


class Attempt(BaseModel):
    attempt_id: UUID
    learner_id: UUID
    submission_id: UUID
    task_version_id: UUID
    attempt_number: int = Field(strict=True, ge=1)
    evaluation_id: UUID
    feedback_id: UUID
    evaluator_id: str = Field(strict=True, min_length=1)
    evaluator_version: str = Field(strict=True, min_length=1)
    prompt_version: str = Field(strict=True, min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class LearnerProgress(BaseModel):
    learner_id: UUID
    current_status: LearnerStatus
    # LearnerProgress stores the stable text task identifier used by tasks.task_id.
    # A task version remains UUID-addressed separately.
    current_task_id: str | None = None
    version: int = Field(strict=True, ge=1)
    updated_at: datetime
    reset_at: datetime | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")

    def advance_status(
        self,
        new_status: LearnerStatus,
        timestamp: datetime,
        evaluation: EvaluationResult | None = None,
        is_final_task: bool = False,
    ) -> "LearnerProgress":
        from yom_awel.domain.state_machine import evaluate_transition, transition

        if new_status in (LearnerStatus.TASK_COMPLETED, LearnerStatus.PROGRAM_COMPLETED):
            if not evaluation:
                raise ValueError("Evaluation authority required for completion")
            final_status = evaluate_transition(
                self.current_status, evaluation, is_final_task=is_final_task
            )
            if final_status != new_status:
                raise ValueError(f"Evaluation resulted in {final_status}, expected {new_status}")
        else:
            transition(self.current_status, new_status)

        return self.model_copy(
            update={
                "current_status": new_status,
                "version": self.version + 1,
                "updated_at": timestamp,
            }
        )


def extract_skill_evidence(
    learner_id: UUID,
    attempt_id: UUID,
    task_version: TaskVersion,
    evaluation: EvaluationResult,
    timestamp: datetime,
) -> list[SkillEvidence]:
    import uuid

    from yom_awel.domain.errors import DomainError

    if evaluation.task_version_id != task_version.task_version_id:
        raise DomainError(
            code="task_version_mismatch",
            message="Evaluation task_version_id does not match TaskVersion",
        )

    evidence = []
    passed_check_ids = {check.check_id for check in evaluation.checks if check.passed}

    for mapping in task_version.skill_mappings:
        if mapping.check_id in passed_check_ids:
            if mapping.weight == 0:
                continue

            evidence_id_str = (
                f"{attempt_id}:{task_version.task_version_id}:{mapping.skill_id}:{mapping.check_id}"
            )
            evidence_id = uuid.uuid5(uuid.NAMESPACE_OID, evidence_id_str)

            evidence.append(
                SkillEvidence(
                    evidence_id=evidence_id,
                    learner_id=learner_id,
                    attempt_id=attempt_id,
                    task_version_id=task_version.task_version_id,
                    skill_id=mapping.skill_id,
                    check_id=mapping.check_id,
                    awarded_points=mapping.weight,
                    available_points=mapping.weight,
                    recorded_at=timestamp,
                )
            )
    return evidence


def aggregate_skill_evidence(evidence_list: list[SkillEvidence]) -> list[SkillSummary]:
    """
    Aggregates skill evidence by summing stored awarded weights per skill.
    The final score is clamped between 0 and 100 to ensure standard display bounds.
    The output list is deterministically sorted by skill_id.
    Empty inputs produce an empty list.
    """
    from collections import defaultdict

    scores: dict[str, int] = defaultdict(int)
    for evidence in evidence_list:
        scores[evidence.skill_id] += evidence.awarded_points

    return [
        SkillSummary(skill_id=skill_id, score=min(100, max(0, score)))
        for skill_id, score in sorted(scores.items())
    ]
