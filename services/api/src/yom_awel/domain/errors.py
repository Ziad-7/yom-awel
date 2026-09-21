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
