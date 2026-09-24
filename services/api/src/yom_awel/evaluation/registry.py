"""Explicit (evaluator_id, evaluator_version) routing with no fallback to another version."""

from collections.abc import Mapping

from yom_awel.domain.contracts import ArtifactRef, EvaluationResult, TaskVersion
from yom_awel.domain.errors import DomainError
from yom_awel.ports.evaluation import Evaluator

EvaluatorKey = tuple[str, str]


class UnknownEvaluator(DomainError):
    def __init__(self, evaluator_id: str, evaluator_version: str) -> None:
        super().__init__(
            "unknown_evaluator",
            f"No evaluator registered for {evaluator_id}@{evaluator_version}",
            evaluator_id=evaluator_id,
            evaluator_version=evaluator_version,
        )


class EvaluatorRegistry:
    """Implements the ``Evaluator`` port by delegating to the exact registered version."""

    def __init__(self, evaluators: Mapping[EvaluatorKey, Evaluator]) -> None:
        self._evaluators = dict(evaluators)

    def resolve(self, evaluator_id: str, evaluator_version: str) -> Evaluator:
        try:
            return self._evaluators[(evaluator_id, evaluator_version)]
        except KeyError:
            raise UnknownEvaluator(evaluator_id, evaluator_version) from None

    async def evaluate(self, task_version: TaskVersion, artifact: ArtifactRef) -> EvaluationResult:
        evaluator = self.resolve(task_version.evaluator_id, task_version.evaluator_version)
        return await evaluator.evaluate(task_version, artifact)
