import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from yom_awel.domain.contracts import (
    ApplicationError,
    EvaluationCheck,
    EvaluationError,
    EvaluationResult,
    FeedbackResult,
    SkillMapping,
    SkillsProfile,
    SkillSummary,
    SubmissionOutcome,
    TaskVersion,
)
from yom_awel.domain.enums import ErrorCategory, LearnerStatus, TaskStatus

ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = ROOT / "contracts" / "fixtures"


def dump_fixture(filename: str, model_cls: type[BaseModel], **kwargs: Any) -> None:
    obj = model_cls(**kwargs)
    path = FIXTURES_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj.model_dump(mode="json"), f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def main() -> None:
    task_version_id = UUID("00000000-0000-0000-0000-000000000001")
    submission_id = UUID("00000000-0000-0000-0000-000000000002")
    attempt_id = UUID("00000000-0000-0000-0000-000000000003")
    learner_id = UUID("00000000-0000-0000-0000-000000000004")

    task_version = TaskVersion(
        task_version_id=task_version_id,
        task_id="clean-sales",
        version="1",
        instructions_ar="نظّف بيانات المبيعات وفق القواعد المحددة.",
        instructions_en="Clean the sales data according to the defined rules.",
        artifact_schema={
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "format": {"enum": ["xlsx", "csv"]},
            },
            "required": ["filename", "format"],
        },
        evaluator_id="sales-cleaning",
        evaluator_version="1",
        pass_threshold=75,
        skill_mappings=[SkillMapping(skill_id="data_cleaning", check_id="clean_data", weight=25)],
        content_hash="b" * 64,
    )
    dump_fixture("task-version-clean-sales.json", TaskVersion, **task_version.model_dump())

    eval_pass = {
        "evaluator_id": "sales-cleaning",
        "evaluator_version": "1",
        "task_version_id": task_version_id,
        "passed": True,
        "score": 100,
        "checks": [EvaluationCheck(check_id="clean_data", passed=True, weight=100)],
        "errors": [],
        "summary_ar": "نجاح",
        "summary_en": "Success",
        "duration_ms": 1500,
    }
    dump_fixture("evaluation-pass.json", EvaluationResult, **eval_pass)

    eval_fail = eval_pass.copy()
    eval_fail.update(
        {
            "passed": False,
            "score": 0,
            "checks": [
                EvaluationCheck(
                    check_id="clean_data", passed=False, weight=100, details="Missing rows"
                )
            ],
            "errors": [EvaluationError(code="missing_data", message="Data is incomplete")],
            "summary_ar": "فشل",
            "summary_en": "Failure",
        }
    )
    dump_fixture("evaluation-fail.json", EvaluationResult, **eval_fail)

    feedback_gen = {
        "feedback_text": "Good job!",
        "language": "en",
        "persona_id": "tarek",
        "prompt_version": "tarek-feedback@1",
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "used_fallback": False,
        "duration_ms": 2000,
    }
    dump_fixture("feedback-generated.json", FeedbackResult, **feedback_gen)

    feedback_fallback = feedback_gen.copy()
    feedback_fallback.update(
        {
            "feedback_text": "Fallback message",
            "language": "ar-EG",
            "persona_id": "tarek",
            "provider": "deterministic",
            "model": None,
            "used_fallback": True,
        }
    )
    dump_fixture("feedback-fallback.json", FeedbackResult, **feedback_fallback)

    sub_pass = {
        "submission_id": submission_id,
        "attempt_id": attempt_id,
        "attempt_number": 1,
        "evaluation": EvaluationResult(**eval_pass),
        "feedback": FeedbackResult(**feedback_gen),
        "learner_status": LearnerStatus.TASK_COMPLETED,
        "task_status": TaskStatus.COMPLETED,
        "skills": [SkillSummary(skill_id="data_cleaning", score=100)],
    }
    dump_fixture("submission-pass.json", SubmissionOutcome, **sub_pass)

    sub_fail = sub_pass.copy()
    sub_fail.update(
        {
            "evaluation": EvaluationResult(**eval_fail),
            "feedback": FeedbackResult(**feedback_fallback),
            "learner_status": LearnerStatus.NEEDS_RETRY,
            "task_status": TaskStatus.ACTIVE,
            "skills": [SkillSummary(skill_id="data_cleaning", score=0)],
        }
    )
    dump_fixture("submission-fail.json", SubmissionOutcome, **sub_fail)
    dump_fixture("submission-duplicate.json", SubmissionOutcome, **sub_pass)

    dump_fixture(
        "skills-profile.json",
        SkillsProfile,
        learner_id=learner_id,
        skills=[SkillSummary(skill_id="data_cleaning", score=100)],
    )
    dump_fixture(
        "application-error.json",
        ApplicationError,
        code="invalid_format",
        category=ErrorCategory.VALIDATION,
        message="File format not supported",
        retryable=False,
    )


if __name__ == "__main__":
    main()
