from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Persona:
    persona_id: str
    name_ar: str
    name_en: str
    workplace_role: str
    workplace_role_en: str
    language: str
    tone_rules: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    status: Literal["active", "roadmap"]


PERSONAS = {
    "tarek": Persona(
        persona_id="tarek",
        name_ar="م. طارق",
        name_en="Eng. Tarek",
        workplace_role="مشرف الفريق",
        workplace_role_en="Team Lead",
        language="ar-EG",
        tone_rules=("professional", "concise", "supportive", "egyptian-arabic"),
        allowed_actions=("explain_evaluation", "explain_business_impact", "suggest_next_step"),
        prohibited_actions=("override_grade", "reveal_reference_solution", "invent_errors"),
        status="active",
    ),
    "hazem": Persona(
        persona_id="hazem",
        name_ar="حازم",
        name_en="Hazem",
        workplace_role="زميل بالفريق",
        workplace_role_en="Teammate",
        language="ar-EG",
        tone_rules=("peer-like", "supportive"),
        allowed_actions=("encourage",),
        prohibited_actions=("override_grade", "reveal_reference_solution"),
        status="roadmap",
    ),
    "mona": Persona(
        persona_id="mona",
        name_ar="منى",
        name_en="Mona",
        workplace_role="مديرة القسم",
        workplace_role_en="Department Manager",
        language="ar-EG",
        tone_rules=("professional", "business-focused"),
        allowed_actions=("explain_business_impact",),
        prohibited_actions=("override_grade", "reveal_reference_solution"),
        status="roadmap",
    ),
}
