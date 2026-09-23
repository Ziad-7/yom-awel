from dataclasses import dataclass


@dataclass
class FeedbackProviderError(Exception):
    code: str
    retryable: bool = False
    retry_after_seconds: float | None = None

    def __str__(self) -> str:
        return self.code


class MissingCredentialsError(FeedbackProviderError):
    def __init__(self) -> None:
        super().__init__(code="missing_credentials")


class ProviderTimeoutError(FeedbackProviderError):
    def __init__(self) -> None:
        super().__init__(code="timeout")


class ProviderNetworkError(FeedbackProviderError):
    def __init__(self, retry_after_seconds: float | None = None) -> None:
        super().__init__(code="network", retryable=True, retry_after_seconds=retry_after_seconds)


class ProviderQuotaError(FeedbackProviderError):
    def __init__(self, retry_after_seconds: float | None = None) -> None:
        super().__init__(code="quota", retryable=True, retry_after_seconds=retry_after_seconds)


class ProviderRefusalError(FeedbackProviderError):
    def __init__(self) -> None:
        super().__init__(code="refusal")


class ProviderResponseError(FeedbackProviderError):
    def __init__(self, code: str = "invalid_response") -> None:
        super().__init__(code=code)
