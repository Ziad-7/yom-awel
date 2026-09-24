"""Explicit local integration fixtures, never an authoritative production grader."""

from pathlib import Path

from yom_awel.domain.contracts import ArtifactRef, EvaluationResult, TaskVersion

DATA = Path(__file__).with_name("demo_data")
DIRTY_CSV = (
    b"order_id,date,quantity,revenue,customer_email\n1,2026/09/01,-2,100,\n1,2026/09/01,-2,100,\n"
)
CLEAN_CSV = (
    b"order_id,date,quantity,revenue,customer_email\n1,2026-09-01,2,100,customer@example.test\n"
)


def demo_task() -> TaskVersion:
    return TaskVersion.model_validate_json(
        (DATA / "task-version-clean-sales.json").read_text(encoding="utf-8")
    )


class FixtureEvaluator:
    async def evaluate(self, task_version: TaskVersion, artifact: ArtifactRef) -> EvaluationResult:
        # Exact canned fixture selection, not a duplicate implementation of member4's grader.
        fixture = (
            "evaluation-pass.json" if artifact.content == CLEAN_CSV else "evaluation-fail.json"
        )
        result = EvaluationResult.model_validate_json((DATA / fixture).read_text(encoding="utf-8"))
        return result.model_copy(update={"task_version_id": task_version.task_version_id})
