"""Evaluation-to-feedback slice: the real clean-sales@1 evaluator feeds Tarek's feedback."""

import csv
import io
import json
from pathlib import Path
from uuid import UUID

import pytest

from tests.evaluation.support import TASK_VERSION, artifact_ref, to_xlsx
from yom_awel.domain.contracts import EvaluationResult, TaskVersion
from yom_awel.domain.enums import Language
from yom_awel.evaluation.clean_sales_dataset import (
    LEARNER_SEED,
    Row,
    apply_defects,
    generate,
    to_csv,
)
from yom_awel.evaluation.sales_cleaning import SalesCleaningEvaluator
from yom_awel.feedback.config import FeedbackConfig, build_feedback_provider
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.parser import validate_grounded_feedback
from yom_awel.feedback.prompt import build_provider_request

ROOT = Path(__file__).resolve().parents[4]
PACKAGE_ROOT = ROOT / "task_packages" / "clean-sales" / "1"
LEARNER = generate(LEARNER_SEED)
DUPLICATES = [defect for defect in LEARNER.defects if defect.kind == "duplicate_order"]
FAKE_KEY = "fake-gemini-key-for-tests-only"
DIRTY_CSV = (PACKAGE_ROOT / "data" / "sales_dirty.csv").read_bytes()


def csv_rows(content: bytes) -> list[Row]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def encode(rows: list[Row], file_format: str) -> bytes:
    return to_csv(rows).encode() if file_format == "csv" else to_xlsx(rows)


ROWS: dict[str, list[Row]] = {
    "dirty": csv_rows(DIRTY_CSV),
    "clean": list(LEARNER.clean),
    "duplicates-only": list(apply_defects(LEARNER.clean, DUPLICATES)),
    "rejected": list(LEARNER.clean[:10]),
}
# (passed, score, failed checks, rejection code) the evaluator must report per file.
EXPECTED: dict[str, tuple[bool, int, set[str], str | None]] = {
    "dirty": (
        False,
        0,
        {"unique_orders", "standard_dates", "valid_numeric_values", "complete_customer_records"},
        None,
    ),
    "clean": (True, 100, set(), None),
    "duplicates-only": (False, 75, {"unique_orders"}, None),
    "rejected": (
        False,
        0,
        {"unique_orders", "standard_dates", "valid_numeric_values", "complete_customer_records"},
        "too_few_rows",
    ),
}
DECISION = {
    Language.AR_EG: {True: "القرار: التسليم مقبول", False: "القرار: التسليم محتاج إعادة شغل"},
    Language.EN: {
        True: "Decision: submission accepted",
        False: "Decision: submission needs rework",
    },
}
EVALUATOR = SalesCleaningEvaluator.from_directory(PACKAGE_ROOT, clock=lambda: 0)


async def evaluate(case: str, file_format: str) -> EvaluationResult:
    content = encode(ROWS[case], file_format)
    return await EVALUATOR.evaluate(
        TASK_VERSION, artifact_ref(content, f"sales_cleaned.{file_format}")
    )


class EchoingGeminiClient:
    """Fake Gemini: returns the approved text, as the prompt instructs a compliant model to."""

    async def generate_json(self, *, model: str, prompt: str, timeout_seconds: float) -> str:
        del model, timeout_seconds
        request = json.loads(prompt)
        evaluation = request["structured_evaluation"]
        language = "ar-EG" if "Egyptian Arabic" in request["system_policy"] else "en"
        return json.dumps(
            {
                "feedback_text": request["approved_feedback_text"],
                "language": language,
                "decision": "pass" if evaluation["passed"] else "retry",
                "score": evaluation["score"],
                "referenced_check_ids": [
                    check["check_id"] for check in evaluation["checks"] if not check["passed"]
                ],
                "reveals_reference_solution": False,
            },
            ensure_ascii=False,
        )


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("file_format", ["csv", "xlsx"])
@pytest.mark.parametrize("case", list(ROWS))
async def test_real_evaluation_flows_into_grounded_feedback(
    case: str, file_format: str, language: Language
) -> None:
    evaluation = await evaluate(case, file_format)
    passed, score, failed, rejection = EXPECTED[case]
    assert (evaluation.passed, evaluation.score) == (passed, score)
    assert {check.check_id for check in evaluation.checks if not check.passed} == failed
    assert [error.code for error in evaluation.errors] == ([rejection] if rejection else [])

    feedback = await DeterministicFeedbackProvider().generate(evaluation, language)
    validate_grounded_feedback(feedback, evaluation, language)
    assert feedback.feedback_text.splitlines()[1].startswith(DECISION[language][passed])

    request = build_provider_request(TASK_VERSION, evaluation, None, language)
    assert request.approved_feedback_text == feedback.feedback_text
    assert [error.code for error in request.structured_evaluation.errors] == [
        error.code for error in evaluation.errors
    ]
    emails = {row["customer_email"] for row in ROWS[case]} - {""}
    assert not [email for email in emails if email in request.serialized()]


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("case", list(ROWS))
async def test_csv_and_xlsx_get_identical_feedback(case: str, language: Language) -> None:
    csv_result, xlsx_result = [await evaluate(case, fmt) for fmt in ("csv", "xlsx")]
    assert DeterministicFeedbackProvider.render_text(
        csv_result, language
    ) == DeterministicFeedbackProvider.render_text(xlsx_result, language)


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("case", list(ROWS))
async def test_compliant_gemini_output_is_accepted_for_every_real_state(
    case: str, language: Language
) -> None:
    async def resolve(task_version_id: UUID) -> TaskVersion:
        assert task_version_id == TASK_VERSION.task_version_id
        return TASK_VERSION

    evaluation = await evaluate(case, "xlsx")
    provider = build_feedback_provider(
        FeedbackConfig.from_env({"GEMINI_API_KEY": FAKE_KEY}),
        task_context_resolver=resolve,
        client=EchoingGeminiClient(),
    )
    result = await provider.generate(evaluation, language)
    assert (result.provider, result.used_fallback) == ("gemini", False)
    approved = DeterministicFeedbackProvider.render_text(evaluation, language)
    assert result.feedback_text == " ".join(approved.split())
