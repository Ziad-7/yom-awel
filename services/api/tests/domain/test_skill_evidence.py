from datetime import UTC, datetime
from uuid import uuid4

import pytest

from yom_awel.domain.contracts import (
    EvaluationCheck,
    EvaluationResult,
    SkillMapping,
    TaskVersion,
)
from yom_awel.domain.entities import (
    SkillEvidence,
    aggregate_skill_evidence,
    extract_skill_evidence,
)


def test_extract_skill_evidence_only_passed_checks() -> None:
    learner_id = uuid4()
    attempt_id = uuid4()
    task_version_id = uuid4()
    timestamp = datetime.now(UTC)

    task_version = TaskVersion(
        task_version_id=task_version_id,
        task_id="test",
        version="1",
        instructions_ar="test",
        instructions_en="test",
        artifact_schema={},
        evaluator_id="test",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[
            SkillMapping(skill_id="skill1", check_id="check1", weight=20),
            SkillMapping(skill_id="skill2", check_id="check2", weight=30),
        ],
        content_hash="a" * 64,
    )

    evaluation = EvaluationResult(
        evaluator_id="test",
        evaluator_version="1",
        task_version_id=task_version_id,
        passed=False,
        score=20,
        checks=[
            EvaluationCheck(check_id="check1", passed=True, weight=20),
            EvaluationCheck(check_id="check2", passed=False, weight=30),
        ],
        errors=[],
        summary_ar="test",
        summary_en="test",
        duration_ms=100,
    )

    evidence = extract_skill_evidence(learner_id, attempt_id, task_version, evaluation, timestamp)

    assert len(evidence) == 1
    ev = evidence[0]
    assert ev.skill_id == "skill1"
    assert ev.check_id == "check1"
    assert ev.awarded_points == 20
    assert ev.available_points == 20
    assert ev.learner_id == learner_id
    assert ev.attempt_id == attempt_id
    assert ev.task_version_id == task_version_id


def test_aggregate_skill_evidence_clamps_to_100() -> None:
    evidence = [
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="skill1",
            check_id="check1",
            awarded_points=60,
            available_points=60,
            recorded_at=datetime.now(UTC),
        ),
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="skill1",
            check_id="check2",
            awarded_points=50,
            available_points=50,
            recorded_at=datetime.now(UTC),
        ),
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="skill2",
            check_id="check3",
            awarded_points=30,
            available_points=30,
            recorded_at=datetime.now(UTC),
        ),
    ]

    summaries = aggregate_skill_evidence(evidence)

    assert len(summaries) == 2

    # Sort order is deterministic from dict items sorted by skill_id
    assert summaries[0].skill_id == "skill1"
    assert summaries[0].score == 100  # clamped from 110

    assert summaries[1].skill_id == "skill2"
    assert summaries[1].score == 30


def test_skill_evidence_rejects_invalid_points() -> None:
    with pytest.raises(ValueError, match="awarded_points cannot exceed available_points"):
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="skill1",
            check_id="check1",
            awarded_points=20,
            available_points=10,
            recorded_at=datetime.now(UTC),
        )

    with pytest.raises(ValueError):
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="skill1",
            check_id="check1",
            awarded_points=0,
            available_points=0,
            recorded_at=datetime.now(UTC),
        )


def test_extract_evidence_task_version_mismatch() -> None:
    task_version = TaskVersion(
        task_version_id=uuid4(),
        task_id="test",
        version="1",
        instructions_ar="test",
        instructions_en="test",
        artifact_schema={},
        evaluator_id="test",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[],
        content_hash="a" * 64,
    )

    evaluation = EvaluationResult(
        evaluator_id="test",
        evaluator_version="1",
        task_version_id=uuid4(),  # Different!
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="test",
        summary_en="test",
        duration_ms=100,
    )
    from yom_awel.domain.errors import DomainError

    with pytest.raises(DomainError) as exc:
        extract_skill_evidence(uuid4(), uuid4(), task_version, evaluation, datetime.now(UTC))

    assert exc.value.code == "task_version_mismatch"


def test_aggregate_skill_evidence_empty() -> None:
    assert aggregate_skill_evidence([]) == []


def test_aggregate_skill_evidence_deterministic_sort() -> None:
    evidence = [
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="b_skill",
            check_id="check1",
            awarded_points=10,
            available_points=10,
            recorded_at=datetime.now(UTC),
        ),
        SkillEvidence(
            evidence_id=uuid4(),
            learner_id=uuid4(),
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="a_skill",
            check_id="check2",
            awarded_points=10,
            available_points=10,
            recorded_at=datetime.now(UTC),
        ),
    ]

    summaries = aggregate_skill_evidence(evidence)
    assert summaries[0].skill_id == "a_skill"
    assert summaries[1].skill_id == "b_skill"


def test_extract_evidence_produces_deterministic_ids() -> None:
    learner_id = uuid4()
    attempt_id = uuid4()
    task_version_id = uuid4()
    timestamp = datetime.now(UTC)

    task_version = TaskVersion(
        task_version_id=task_version_id,
        task_id="test",
        version="1",
        instructions_ar="test",
        instructions_en="test",
        artifact_schema={},
        evaluator_id="test",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[
            SkillMapping(skill_id="skill1", check_id="check1", weight=20),
        ],
        content_hash="a" * 64,
    )

    evaluation = EvaluationResult(
        evaluator_id="test",
        evaluator_version="1",
        task_version_id=task_version_id,
        passed=True,
        score=20,
        checks=[
            EvaluationCheck(check_id="check1", passed=True, weight=20),
        ],
        errors=[],
        summary_ar="test",
        summary_en="test",
        duration_ms=100,
    )

    evidence1 = extract_skill_evidence(learner_id, attempt_id, task_version, evaluation, timestamp)

    evidence2 = extract_skill_evidence(learner_id, attempt_id, task_version, evaluation, timestamp)

    assert evidence1[0].evidence_id == evidence2[0].evidence_id
