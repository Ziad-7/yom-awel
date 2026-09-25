"""Task-specific feedback for files rejected before rubric checks can run."""

import asyncio
import hashlib
from pathlib import Path
from uuid import UUID

import pytest

from yom_awel.domain.contracts import ArtifactRef, EvaluationError
from yom_awel.domain.enums import Language
from yom_awel.evaluation.catalog import TaskCatalog
from yom_awel.feedback.fallback import (
    SECTION_HEADINGS,
    TASK_GUIDANCE,
    TASK_REJECTION_GUIDANCE,
    DeterministicFeedbackProvider,
)
from yom_awel.feedback.parser import validate_grounded_feedback

ROOT = Path(__file__).resolve().parents[4] / "task_packages"


def _evaluate(task_id: str, content: bytes, filename: str):
    task = TaskCatalog.load(ROOT).get(task_id)
    artifact = ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000000001"),
        filename=filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )
    return asyncio.run(
        TaskCatalog.load(ROOT).evaluator_registry().evaluate(task.task_version, artifact)
    )


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize(
    ("task_id", "content", "filename", "code", "irrelevant_check"),
    [
        ("sql-report", b"DROP TABLE sales", "report.sql", "sql_query_rejected", "report_columns"),
        ("sql-report", b"\xff", "report.sql", "artifact_unreadable", "report_columns"),
        ("client-email", b"\xff", "email.txt", "artifact_unreadable", "recipient_and_subject"),
        ("client-email", b"%PDF-1.7", "email.txt", "mime_mismatch", "recipient_and_subject"),
    ],
)
def test_rejected_new_task_feedback_names_the_rejection(
    task_id: str,
    content: bytes,
    filename: str,
    code: str,
    irrelevant_check: str,
    language: Language,
) -> None:
    evaluation = _evaluate(task_id, content, filename)
    assert [error.code for error in evaluation.errors] == [code]
    assert evaluation.score == 0

    feedback = asyncio.run(
        DeterministicFeedbackProvider(clock=lambda: 0).generate(evaluation, language)
    )
    text = feedback.feedback_text
    reason, action = TASK_REJECTION_GUIDANCE[task_id][code][language]
    assert reason in text
    assert action in text
    assert all(text.count(heading) == 1 for heading in SECTION_HEADINGS[language])
    assert len(text) <= 900
    assert TASK_GUIDANCE[irrelevant_check][language][1] not in text
    assert "DROP TABLE sales" not in text
    validate_grounded_feedback(feedback, evaluation, language)


@pytest.mark.parametrize("language", list(Language))
def test_unknown_task_error_never_echoes_untrusted_message(language: Language) -> None:
    evaluation = _evaluate("sql-report", b"DROP TABLE sales", "report.sql")
    unknown = evaluation.model_copy(
        update={"errors": [EvaluationError(code="unknown", message="private@example.com secret")]}
    )

    text = DeterministicFeedbackProvider.render_text(unknown, language)

    assert "private@example.com" not in text
    assert "secret" not in text
    assert "report columns" not in text
    assert len(text) <= 900
