from typing import Protocol

from yom_awel.domain.contracts import ArtifactRef, EvaluationResult, TaskVersion


class Evaluator(Protocol):
    async def evaluate(
        self, task_version: TaskVersion, artifact: ArtifactRef
    ) -> EvaluationResult: ...
