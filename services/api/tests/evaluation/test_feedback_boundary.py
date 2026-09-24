import pytest

from tests.evaluation.support import REFERENCE, TASK_VERSION, evaluate_bytes, evaluate_rows
from yom_awel.domain.contracts import EvaluationResult
from yom_awel.evaluation.clean_sales_dataset import apply_defects
from yom_awel.feedback.prompt import build_provider_request

DUPLICATE = next(defect for defect in REFERENCE.defects if defect.kind == "duplicate_order")


@pytest.mark.parametrize(
    "result",
    [
        evaluate_rows(REFERENCE.clean),
        evaluate_rows(apply_defects(REFERENCE.clean, [DUPLICATE])),
        evaluate_rows(REFERENCE.dirty),
        evaluate_bytes(b"PK\x03\x04 spoofed"),
    ],
    ids=["pass", "retry-critical", "retry-score", "rejection"],
)
def test_feedback_receives_every_check_and_decision_unchanged(result: EvaluationResult) -> None:
    evaluation = build_provider_request(TASK_VERSION, result, None).structured_evaluation

    assert (evaluation.passed, evaluation.score) == (result.passed, result.score)
    assert [(c.check_id, c.passed, c.weight, c.diagnostic_code) for c in evaluation.checks] == [
        (c.check_id, c.passed, c.weight, c.diagnostic_code) for c in result.checks
    ]
