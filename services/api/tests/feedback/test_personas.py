from yom_awel.feedback.personas import PERSONAS
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY


def test_tarek_is_the_only_active_v1_persona() -> None:
    assert ACTIVE_FEEDBACK_POLICY.persona_id == "eng-tarek"
    assert PERSONAS["eng-tarek"].language == "ar-EG"
    assert PERSONAS["hazem"].status == "roadmap"
    assert PERSONAS["mona"].status == "roadmap"
    assert [persona.persona_id for persona in PERSONAS.values() if persona.status == "active"] == [
        "eng-tarek"
    ]


def test_policy_forbids_grade_override_and_solution_disclosure() -> None:
    assert "override_grade" in ACTIVE_FEEDBACK_POLICY.prohibited_actions
    assert "reveal_reference_solution" in ACTIVE_FEEDBACK_POLICY.prohibited_actions
