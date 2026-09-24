import os
from pathlib import Path

import pytest
import yaml

from yom_awel.domain.contracts import EvaluationError, EvaluationResult, FeedbackResult, TaskVersion
from yom_awel.domain.enums import Language
from yom_awel.feedback.fallback import (
    CRITICAL_CHECK_IDS,
    PASS_THRESHOLD,
    REJECTION_ACTIONS,
    REJECTION_MESSAGES,
    DeterministicFeedbackProvider,
)
from yom_awel.feedback.parser import validate_grounded_feedback
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY
from yom_awel.feedback.prompt import build_provider_request

ROOT = Path(__file__).resolve().parents[4]
SNAPSHOTS = Path(__file__).with_name("snapshots")
OBJECTIVES = yaml.safe_load(
    (ROOT / "task_packages/clean-sales/1/learning-objectives.yaml").read_text(encoding="utf-8")
)
REJECTION_CODES = [item["code"] for item in OBJECTIVES["diagnostic_vocabulary"]["rejections"]]
STATES = [
    "pass",
    "pass-with-gap",
    "retry-score",
    "retry-critical",
    "retry-score-critical",
    *(f"rejected-{code}" for code in REJECTION_CODES),
]
BYLINE = {Language.AR_EG: "م. طارق، مشرف الفريق", Language.EN: "Eng. Tarek, Team Lead"}
CRITICAL_SENTENCE = {
    Language.AR_EG: "الطلبات المكررة بتمنع النجاح مهما كانت الدرجة.",
    Language.EN: "Duplicate orders block passing, whatever the score.",
}


def build_state(state: str, passed: EvaluationResult, failed: EvaluationResult) -> EvaluationResult:
    """Evaluations shaped exactly as the clean-sales@1 evaluator emits them."""
    ok, bad = passed.checks, failed.checks
    shapes = {
        "pass": (passed, ok, 100, True),
        "pass-with-gap": (passed, [ok[0], bad[1], *ok[2:]], 75, True),
        "retry-score": (failed, [*ok[:2], *bad[2:]], 50, False),
        "retry-critical": (failed, [bad[0], *ok[1:]], 75, False),
        "retry-score-critical": (failed, bad, 0, False),
    }
    if state.startswith("rejected-"):
        code = state.removeprefix("rejected-")
        error = EvaluationError(code=code, message="row 7: ahmed@example.com 01012345678")
        return failed.model_copy(update={"errors": [error], "score": 0, "passed": False})
    base, checks, score, is_passed = shapes[state]
    return base.model_copy(
        update={"checks": list(checks), "score": score, "passed": is_passed, "errors": []}
    )


def rendered(evaluation: EvaluationResult, language: Language) -> str:
    return DeterministicFeedbackProvider.render_text(evaluation, language)


def as_result(text: str, language: Language) -> FeedbackResult:
    return FeedbackResult(
        feedback_text=text,
        language=language.value,
        persona_id="tarek",
        prompt_version=ACTIVE_FEEDBACK_POLICY.version,
        provider="deterministic",
        model=None,
        used_fallback=True,
        duration_ms=0,
    )


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("state", STATES)
def test_every_state_matches_its_snapshot_and_policy(
    state: str,
    language: Language,
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = build_state(state, passed_evaluation, failed_evaluation)
    text = rendered(evaluation, language)

    snapshot = SNAPSHOTS / f"{state}.{language.value}.txt"
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        snapshot.write_text(text + "\n", encoding="utf-8")
    assert text == snapshot.read_text(encoding="utf-8").rstrip("\n")
    assert len(text) <= ACTIVE_FEEDBACK_POLICY.maximum_characters
    assert text.splitlines()[0] == BYLINE[language]
    validate_grounded_feedback(as_result(text, language), evaluation, language)


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("state", ["retry-critical", "retry-score-critical"])
def test_failed_critical_check_blocks_passing_whatever_the_score(
    state: str,
    language: Language,
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = build_state(state, passed_evaluation, failed_evaluation)
    decision = rendered(evaluation, language).splitlines()[1]
    assert CRITICAL_SENTENCE[language] in decision


@pytest.mark.parametrize("language", list(Language))
def test_high_score_with_duplicates_explains_that_score_alone_is_not_enough(
    language: Language, passed_evaluation: EvaluationResult, failed_evaluation: EvaluationResult
) -> None:
    evaluation = build_state("retry-critical", passed_evaluation, failed_evaluation)
    assert evaluation.score >= PASS_THRESHOLD
    explanation = rendered(evaluation, language).splitlines()[-1]
    expected = {
        Language.AR_EG: "فحص الطلبات المكررة أساسي ولازم ينجح",
        Language.EN: "the duplicate orders check is critical",
    }
    assert expected[language] in explanation


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("state", ["pass", "pass-with-gap", "retry-score"])
def test_critical_sentence_only_appears_when_the_critical_check_failed(
    state: str,
    language: Language,
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = build_state(state, passed_evaluation, failed_evaluation)
    assert CRITICAL_SENTENCE[language] not in rendered(evaluation, language)


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("code", REJECTION_CODES)
def test_rejection_gets_code_specific_guidance_without_file_content(
    code: str,
    language: Language,
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = build_state(f"rejected-{code}", passed_evaluation, failed_evaluation)
    text = rendered(evaluation, language)
    assert REJECTION_MESSAGES[code][language] in text
    assert REJECTION_ACTIONS[code][language] in text
    for leaked in ("row 7", "ahmed@example.com", "01012345678"):
        assert leaked not in text
    other_actions = [REJECTION_ACTIONS[other][language] for other in REJECTION_ACTIONS]
    assert sum(action in text for action in other_actions) == 1


def test_unknown_error_codes_keep_check_based_guidance(
    passed_evaluation: EvaluationResult, failed_evaluation: EvaluationResult
) -> None:
    evaluation = build_state("retry-score", passed_evaluation, failed_evaluation)
    unknown = evaluation.model_copy(
        update={"errors": [EvaluationError(code="storage_glitch", message="x")]}
    )
    assert rendered(unknown, Language.EN) == rendered(evaluation, Language.EN)


def test_rejection_vocabulary_is_verbatim_from_the_task_package() -> None:
    vocabulary = {
        item["code"]: {
            Language.AR_EG: item["learner_message_ar"],
            Language.EN: item["learner_message_en"],
        }
        for item in OBJECTIVES["diagnostic_vocabulary"]["rejections"]
    }
    assert REJECTION_MESSAGES == vocabulary
    assert set(REJECTION_ACTIONS) == set(vocabulary)
    assert all(set(actions) == set(Language) for actions in REJECTION_ACTIONS.values())


def test_restated_grading_policy_matches_the_task_package() -> None:
    policy = OBJECTIVES["pass_policy"]
    assert policy["pass_threshold"] == PASS_THRESHOLD
    assert frozenset(policy["critical_checks"]) == CRITICAL_CHECK_IDS


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("code", REJECTION_CODES)
def test_provider_request_carries_approved_rejection_text(
    code: str,
    language: Language,
    task: TaskVersion,
    passed_evaluation: EvaluationResult,
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = build_state(f"rejected-{code}", passed_evaluation, failed_evaluation)
    request = build_provider_request(task, evaluation, None, language)
    [error] = request.structured_evaluation.errors
    assert (error.code, error.message) == (code, REJECTION_MESSAGES[code][language])
    assert request.approved_feedback_text == rendered(evaluation, language)
    assert "ahmed@example.com" not in request.serialized()
