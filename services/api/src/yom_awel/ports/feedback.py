from typing import Protocol

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language


class FeedbackProvider(Protocol):
    async def generate(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None = None,
    ) -> FeedbackResult: ...
