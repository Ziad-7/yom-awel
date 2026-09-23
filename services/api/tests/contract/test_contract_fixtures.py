import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from yom_awel.domain.contracts import (
    ApplicationError,
    ArtifactRef,
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

ROOT = Path(__file__).resolve().parents[4]

VALID_ARTIFACT_REF = ArtifactRef(
    artifact_id=UUID("00000000-0000-0000-0000-000000000005"),
    filename="sales.xlsx",
    size_bytes=1024,
    sha256="a" * 64,
)
VALID_SKILL_MAPPING = SkillMapping(skill_id="data_cleaning", check_id="clean_data", weight=25)
VALID_TASK_VERSION = TaskVersion(
    task_version_id=UUID("00000000-0000-0000-0000-000000000001"),
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
    skill_mappings=[VALID_SKILL_MAPPING],
    content_hash="b" * 64,
)
VALID_EVALUATION_RESULT = EvaluationResult.model_validate_json(
    (ROOT / "contracts" / "fixtures" / "evaluation-pass.json").read_text(encoding="utf-8")
)
VALID_EVALUATION_CHECK = EvaluationCheck(check_id="clean_data", passed=True, weight=100)
VALID_EVALUATION_ERROR = EvaluationError(code="invalid", message="bad")
VALID_FEEDBACK_RESULT = FeedbackResult.model_validate_json(
    (ROOT / "contracts" / "fixtures" / "feedback-generated.json").read_text(encoding="utf-8")
)
VALID_SKILL_SUMMARY = SkillSummary(skill_id="data_cleaning", score=100)
VALID_SUBMISSION_OUTCOME = SubmissionOutcome.model_validate_json(
    (ROOT / "contracts" / "fixtures" / "submission-pass.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("evaluation-pass.json", EvaluationResult),
        ("evaluation-fail.json", EvaluationResult),
        ("task-version-clean-sales.json", TaskVersion),
        ("feedback-generated.json", FeedbackResult),
        ("feedback-fallback.json", FeedbackResult),
        ("submission-pass.json", SubmissionOutcome),
        ("submission-fail.json", SubmissionOutcome),
        ("submission-duplicate.json", SubmissionOutcome),
        ("skills-profile.json", SkillsProfile),
        ("application-error.json", ApplicationError),
    ],
)
def test_canonical_fixture_validates(filename: str, model: type[BaseModel]) -> None:
    payload = json.loads((ROOT / "contracts" / "fixtures" / filename).read_text(encoding="utf-8"))
    assert model.model_validate(payload).model_dump(mode="json") == payload


def test_duplicate_fixture_is_byte_for_byte_equal_to_success() -> None:
    fixtures = ROOT / "contracts" / "fixtures"
    assert (fixtures / "submission-duplicate.json").read_bytes() == (
        fixtures / "submission-pass.json"
    ).read_bytes()


def test_clean_sales_task_version_example_is_valid() -> None:
    assert VALID_TASK_VERSION.task_id == "clean-sales"
    assert VALID_TASK_VERSION.version == "1"
    assert VALID_TASK_VERSION.pass_threshold == 75
    assert VALID_TASK_VERSION.instructions_ar
    assert VALID_TASK_VERSION.instructions_en
    assert VALID_TASK_VERSION.skill_mappings == [VALID_SKILL_MAPPING]


def test_fallback_fixture_matches_member_three_consumer_contract() -> None:
    payload = json.loads(
        (ROOT / "contracts" / "fixtures" / "feedback-fallback.json").read_text(encoding="utf-8")
    )
    assert payload["language"] == "ar-EG"
    assert payload["provider"] == "deterministic"
    assert payload["model"] is None
    assert payload["used_fallback"] is True
    assert payload["persona_id"] == "tarek"
    assert payload["prompt_version"] == "tarek-feedback@1"

    submission = json.loads(
        (ROOT / "contracts" / "fixtures" / "submission-fail.json").read_text(encoding="utf-8")
    )
    assert submission["feedback"] == payload


@pytest.mark.parametrize(
    ("valid_model", "field", "invalid_value"),
    [
        (VALID_EVALUATION_RESULT, "score", -1),
        (VALID_EVALUATION_RESULT, "score", 101),
        (VALID_SKILL_SUMMARY, "score", -1),
        (VALID_SKILL_SUMMARY, "score", 101),
        (VALID_EVALUATION_RESULT, "duration_ms", -1),
        (VALID_FEEDBACK_RESULT, "duration_ms", -1),
        (VALID_ARTIFACT_REF, "size_bytes", -1),
        (VALID_ARTIFACT_REF, "size_bytes", 5 * 1024 * 1024 + 1),
        (VALID_ARTIFACT_REF, "sha256", "A" * 64),
        (VALID_TASK_VERSION, "version", ""),
        (VALID_TASK_VERSION, "instructions_ar", ""),
        (VALID_TASK_VERSION, "instructions_en", ""),
        (VALID_TASK_VERSION, "pass_threshold", -1),
        (VALID_TASK_VERSION, "pass_threshold", 101),
        (VALID_TASK_VERSION, "content_hash", "A" * 64),
        (VALID_EVALUATION_RESULT, "evaluator_version", ""),
        (VALID_FEEDBACK_RESULT, "prompt_version", ""),
        (VALID_SKILL_MAPPING, "skill_id", ""),
        (VALID_SKILL_MAPPING, "check_id", ""),
        (VALID_SKILL_MAPPING, "weight", -1),
    ],
)
def test_contract_boundaries_reject_invalid_values(
    valid_model: BaseModel, field: str, invalid_value: Any
) -> None:
    payload = valid_model.model_dump(mode="json")
    payload[field] = invalid_value
    with pytest.raises(ValidationError, match=field):
        type(valid_model).model_validate(payload)


def test_artifact_boundary_accepts_zero_and_five_mib() -> None:
    common = {
        "artifact_id": UUID("00000000-0000-0000-0000-000000000005"),
        "filename": "sales.xlsx",
        "sha256": "a" * 64,
    }
    assert ArtifactRef(**common, size_bytes=0).size_bytes == 0
    assert ArtifactRef(**common, size_bytes=5 * 1024 * 1024).size_bytes == 5 * 1024 * 1024


@pytest.mark.parametrize(
    ("valid_model", "path", "invalid_value"),
    [
        (VALID_EVALUATION_RESULT, ("passed",), "true"),
        (VALID_FEEDBACK_RESULT, ("used_fallback",), "false"),
        (VALID_SUBMISSION_OUTCOME, ("evaluation", "passed"), "true"),
        (
            ApplicationError(code="invalid", category="validation", message="bad", retryable=False),
            ("retryable",),
            "false",
        ),
        (VALID_EVALUATION_RESULT, ("score",), "100"),
        (VALID_EVALUATION_RESULT, ("score",), 100.0),
        (VALID_SUBMISSION_OUTCOME, ("evaluation", "duration_ms"), 1500.0),
        (VALID_ARTIFACT_REF, ("size_bytes",), 1024.0),
        (VALID_TASK_VERSION, ("pass_threshold",), 75.0),
        (VALID_SKILL_SUMMARY, ("score",), "100"),
    ],
)
def test_contract_boundaries_reject_coercible_primitives(
    valid_model: BaseModel, path: tuple[str, ...], invalid_value: Any
) -> None:
    payload = valid_model.model_dump(mode="json")
    nested_payload = payload
    for field in path[:-1]:
        nested_payload = nested_payload[field]
    nested_payload[path[-1]] = invalid_value
    with pytest.raises(ValidationError, match=path[-1]):
        type(valid_model).model_validate(payload)


@pytest.mark.parametrize(
    ("valid_model", "path", "invalid_value"),
    [
        (VALID_ARTIFACT_REF, ("filename",), b"sales.xlsx"),
        (VALID_ARTIFACT_REF, ("sha256",), b"a" * 64),
        (VALID_SKILL_MAPPING, ("skill_id",), b"data_cleaning"),
        (VALID_SKILL_MAPPING, ("check_id",), 123),
        (VALID_TASK_VERSION, ("task_id",), b"clean-sales"),
        (VALID_TASK_VERSION, ("version",), 1),
        (VALID_TASK_VERSION, ("instructions_ar",), b"arabic"),
        (VALID_TASK_VERSION, ("instructions_en",), 123),
        (VALID_TASK_VERSION, ("evaluator_id",), b"sales-cleaning"),
        (VALID_TASK_VERSION, ("evaluator_version",), 1),
        (VALID_TASK_VERSION, ("content_hash",), b"b" * 64),
        (VALID_EVALUATION_RESULT, ("evaluator_id",), b"sales-cleaning"),
        (VALID_EVALUATION_RESULT, ("evaluator_version",), 1),
        (VALID_EVALUATION_RESULT, ("summary_ar",), b"arabic-summary"),
        (VALID_EVALUATION_RESULT, ("summary_en",), 123),
        (VALID_EVALUATION_CHECK, ("check_id",), b"clean_data"),
        (VALID_EVALUATION_CHECK, ("details",), 123),
        (VALID_EVALUATION_ERROR, ("code",), b"invalid"),
        (VALID_EVALUATION_ERROR, ("message",), 123),
        (VALID_FEEDBACK_RESULT, ("feedback_text",), b"Good job!"),
        (VALID_FEEDBACK_RESULT, ("persona_id",), 123),
        (VALID_FEEDBACK_RESULT, ("prompt_version",), b"tarek-feedback@1"),
        (VALID_FEEDBACK_RESULT, ("provider",), 123),
        (VALID_FEEDBACK_RESULT, ("model",), b"gemini-1.5-flash"),
        (VALID_SKILL_SUMMARY, ("skill_id",), b"data_cleaning"),
        (
            ApplicationError(code="invalid", category="validation", message="bad", retryable=False),
            ("code",),
            b"invalid",
        ),
        (
            ApplicationError(code="invalid", category="validation", message="bad", retryable=False),
            ("message",),
            123,
        ),
    ],
)
def test_canonical_string_fields_reject_non_strings(
    valid_model: BaseModel, path: tuple[str | int, ...], invalid_value: Any
) -> None:
    payload = valid_model.model_dump(mode="json")
    nested_payload = payload
    for field in path[:-1]:
        nested_payload = nested_payload[field]
    nested_payload[path[-1]] = invalid_value
    with pytest.raises(ValidationError, match=str(path[-1])):
        type(valid_model).model_validate(payload)


def test_task_version_rejects_non_json_artifact_schema() -> None:
    payload = VALID_TASK_VERSION.model_dump(mode="json")
    payload["artifact_schema"] = {"invalid": object()}
    with pytest.raises(ValidationError, match="artifact_schema"):
        TaskVersion.model_validate(payload)


@pytest.mark.parametrize(
    "model",
    [
        ArtifactRef,
        SkillMapping,
        TaskVersion,
        EvaluationCheck,
        EvaluationError,
        EvaluationResult,
        FeedbackResult,
        SkillSummary,
        SkillsProfile,
        SubmissionOutcome,
        ApplicationError,
    ],
)
def test_canonical_models_reject_extra_fields(model: type[BaseModel]) -> None:
    with pytest.raises(ValidationError, match="unexpected_field"):
        model.model_validate({"unexpected_field": True})


def test_task_version_schema_declares_constraints() -> None:
    schema = TaskVersion.model_json_schema()
    properties = schema["properties"]
    assert properties["instructions_ar"]["minLength"] == 1
    assert properties["instructions_en"]["minLength"] == 1
    assert properties["pass_threshold"]["minimum"] == 0
    assert properties["pass_threshold"]["maximum"] == 100
    assert properties["content_hash"]["pattern"] == r"^[a-f0-9]{64}$"
    skill_mapping = schema["$defs"]["SkillMapping"]["properties"]
    assert skill_mapping["weight"]["minimum"] == 0


def test_generation_scripts_are_root_relative_and_deterministic() -> None:
    fixture_paths = sorted((ROOT / "contracts" / "fixtures").glob("*.json"))
    schema_paths = sorted((ROOT / "contracts" / "schemas").glob("*.json"))
    commands = [
        ROOT / "services" / "api" / "scripts" / "generate_fixtures.py",
        ROOT / "services" / "api" / "scripts" / "export_schemas.py",
    ]
    original = {path: path.read_bytes() for path in fixture_paths + schema_paths}
    source_path = str(ROOT / "services" / "api" / "src")
    existing_pythonpath = os.environ.get("PYTHONPATH")
    pythonpath = os.pathsep.join(path for path in (source_path, existing_pythonpath) if path)
    environment = {**os.environ, "PYTHONPATH": pythonpath}
    for script in commands:
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, env=environment)
    after_first_run = {path: path.read_bytes() for path in fixture_paths + schema_paths}
    assert after_first_run == original
    for script in commands:
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, env=environment)
    after_second_run = {path: path.read_bytes() for path in fixture_paths + schema_paths}
    assert after_second_run == original
