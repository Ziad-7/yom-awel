from typing import Any


class DomainError(Exception):
    def __init__(self, code: str, message: str, **kwargs: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = kwargs


class InvalidTransition(DomainError):
    def __init__(self, current: str, target: str, message: str | None = None) -> None:
        super().__init__(
            code="invalid_transition",
            message=message or f"Cannot transition from {current} to {target}",
            current=current,
            target=target,
        )


class PersistenceError(DomainError):
    """Base error for adapter failures that callers may handle safely."""

    def __init__(self, code: str, message: str, **kwargs: Any) -> None:
        super().__init__(code=code, message=message, **kwargs)


class UniqueConstraintViolation(PersistenceError):
    def __init__(self, constraint: str, message: str | None = None) -> None:
        super().__init__(
            "unique_constraint",
            message or f"Unique constraint violated: {constraint}",
            constraint=constraint,
        )


class OptimisticConflict(PersistenceError):
    def __init__(self, resource: str = "resource", message: str | None = None) -> None:
        super().__init__(
            "optimistic_conflict", message or f"{resource} changed concurrently", resource=resource
        )


class IdempotencyConflict(PersistenceError):
    def __init__(self, key: str, message: str | None = None) -> None:
        super().__init__(
            "idempotency_conflict", message or "Idempotency key has a different request", key=key
        )


class LearnerScopeViolation(PersistenceError):
    def __init__(self, resource: str = "resource") -> None:
        super().__init__(
            "learner_scope_violation", "Resource does not belong to learner", resource=resource
        )


class NotFound(PersistenceError):
    def __init__(self, resource: str) -> None:
        super().__init__("not_found", f"{resource} was not found", resource=resource)


class FinalizationConflict(PersistenceError):
    def __init__(self, message: str = "Reservation cannot be finalized") -> None:
        super().__init__("finalization_conflict", message)


class ReservationOwnerConflict(PersistenceError):
    def __init__(self) -> None:
        super().__init__("reservation_owner_conflict", "Reservation is owned by another processor")


class ReservationExpired(PersistenceError):
    def __init__(self) -> None:
        super().__init__("reservation_expired", "Reservation lease has expired")


class TransactionReuse(PersistenceError):
    def __init__(self) -> None:
        super().__init__("transaction_reuse", "Unit of work is already active")


class SubmissionMismatch(PersistenceError):
    def __init__(self, message: str = "Submission does not match reservation") -> None:
        super().__init__("submission_mismatch", message)


class TaskNotCurrent(PersistenceError):
    def __init__(self) -> None:
        super().__init__("task_not_current", "Submission task is not the learner's current task")
