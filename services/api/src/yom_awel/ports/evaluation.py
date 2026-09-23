from typing import Protocol

from yom_awel.domain.contracts import ArtifactRef, EvaluationResult, TaskVersion


class Evaluator(Protocol):
    """Grades artifact bytes that the application already loaded after its ownership check.

    Evaluators never read storage, learner progression, or provider APIs themselves.
    """

    async def evaluate(
        self, task_version: TaskVersion, artifact: ArtifactRef, content: bytes
    ) -> EvaluationResult: ...
