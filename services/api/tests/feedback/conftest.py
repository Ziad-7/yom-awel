import json
from pathlib import Path

import pytest

from yom_awel.domain.contracts import EvaluationResult, TaskVersion

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def task() -> TaskVersion:
    payload = json.loads(
        (ROOT / "contracts/fixtures/task-version-clean-sales.json").read_text(encoding="utf-8")
    )
    return TaskVersion.model_validate(payload)


@pytest.fixture
def passed_evaluation() -> EvaluationResult:
    payload = json.loads(
        (ROOT / "contracts/fixtures/evaluation-pass.json").read_text(encoding="utf-8")
    )
    return EvaluationResult.model_validate(payload)


@pytest.fixture
def failed_evaluation() -> EvaluationResult:
    payload = json.loads(
        (ROOT / "contracts/fixtures/evaluation-fail.json").read_text(encoding="utf-8")
    )
    return EvaluationResult.model_validate(payload)
