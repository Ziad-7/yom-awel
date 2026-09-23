import json
from pathlib import Path

from pydantic import BaseModel

from yom_awel.domain.contracts import (
    ApplicationError,
    EvaluationResult,
    FeedbackResult,
    SkillsProfile,
    SubmissionOutcome,
    TaskVersion,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_DIR = ROOT / "contracts" / "schemas"


def export_schema(filename: str, model: type[BaseModel]) -> None:
    path = SCHEMAS_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = model.model_json_schema()
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")


def main() -> None:
    export_schema("evaluation-result.json", EvaluationResult)
    export_schema("feedback-result.json", FeedbackResult)
    export_schema("task-version.json", TaskVersion)
    export_schema("submission-outcome.json", SubmissionOutcome)
    export_schema("skills-profile.json", SkillsProfile)
    export_schema("application-error.json", ApplicationError)


if __name__ == "__main__":
    main()
