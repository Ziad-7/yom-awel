from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedbackPolicy:
    version: str
    persona_id: str
    required_sections: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    maximum_characters: int


ACTIVE_FEEDBACK_POLICY = FeedbackPolicy(
    version="tarek-feedback@1",
    persona_id="eng-tarek",
    required_sections=("decision", "business_consequence", "next_action", "score_explanation"),
    prohibited_actions=(
        "override_grade",
        "reveal_reference_solution",
        "harass_learner",
        "invent_errors",
        "expose_secrets",
        "claim_learner_identity",
    ),
    maximum_characters=900,
)

