import json
from pathlib import Path

import pytest

from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.fallback import DeterministicFeedbackProvider

CASES_PATH = Path(__file__).with_name("quality_cases.json")
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
async def test_deterministic_quality_case(
    case: dict[str, object],
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = passed_evaluation if case["fixture"] == "pass" else failed_evaluation
    if case["id"] == "three-failures":
        failed_check = next(check for check in evaluation.checks if not check.passed)
        evaluation = evaluation.model_copy(
            update={
                "checks": [
                    *evaluation.checks,
                    failed_check.model_copy(update={"check_id": "date-format"}),
                    failed_check.model_copy(update={"check_id": "sales-total"}),
                ]
            }
        )
    if case["score_override"] is not None:
        evaluation = evaluation.model_copy(update={"score": case["score_override"]})
    result = await DeterministicFeedbackProvider().generate(
        evaluation, Language.AR_EG, case["learner_note"]  # type: ignore[arg-type]
    )
    assert len(result.feedback_text) <= 900
    assert str(evaluation.score) in result.feedback_text
    for required in case["required"]:  # type: ignore[union-attr]
        assert required in result.feedback_text
    for forbidden in case["forbidden"]:  # type: ignore[union-attr]
        assert forbidden not in result.feedback_text


async def test_fallback_snapshots(
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    snapshots = Path(__file__).with_name("snapshots")
    provider = DeterministicFeedbackProvider()
    passed = await provider.generate(passed_evaluation, Language.AR_EG, None)
    failed = await provider.generate(failed_evaluation, Language.AR_EG, None)
    assert passed.feedback_text == (snapshots / "fallback-pass.txt").read_text(
        encoding="utf-8"
    ).rstrip("\n")
    assert failed.feedback_text == (snapshots / "fallback-fail.txt").read_text(
        encoding="utf-8"
    ).rstrip("\n")
