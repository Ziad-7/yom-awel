from fastapi import Request
from fastapi.responses import JSONResponse

from yom_awel.domain.contracts import ApplicationError
from yom_awel.domain.enums import ErrorCategory
from yom_awel.domain.errors import DomainError, PersistenceError

STATUS = {
    "invalid_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "learner_scope_violation": 403,
    "not_found": 404,
    "learner_not_found": 404,
    "artifact_not_found": 404,
    "idempotency_conflict": 409,
    "optimistic_conflict": 409,
    "unique_constraint": 409,
    "task_not_current": 409,
    "invalid_status": 409,
    "artifact_not_ready": 409,
    "finalization_conflict": 409,
    "reservation_expired": 409,
    "reservation_owner_conflict": 409,
    "artifact_integrity_failure": 422,
    "invalid_artifact": 422,
    "invalid_evaluator": 422,
    "artifact_type_mismatch": 415,
    "unsafe_artifact": 415,
    "too_large": 413,
    "unsupported_artifact": 415,
    "rate_limited": 429,
    "unavailable": 503,
    "supabase_provider_error": 503,
    "evaluation_failed": 503,
}

RETRYABLE_CONFLICTS = {
    "finalization_conflict",
    "reservation_expired",
    "reservation_owner_conflict",
    "optimistic_conflict",
}


def error_response(
    code: str,
    status: int,
    *,
    category: ErrorCategory | None = None,
    retryable: bool | None = None,
    retry_after: int | None = None,
) -> JSONResponse:
    if category is None:
        category = ErrorCategory.AUTHORIZATION if status in (401, 403) else ErrorCategory.VALIDATION
        if status >= 500:
            category = ErrorCategory.INFRASTRUCTURE
    if retryable is None:
        retryable = status in (429, 503)
    message = "تعذّر إكمال الطلب. راجع البيانات وحاول تاني."
    if status == 401:
        message = "الجلسة انتهت. ابدأ جلسة جديدة."
    error = ApplicationError(code=code, category=category, message=message, retryable=retryable)
    return JSONResponse(
        error.model_dump(mode="json"),
        status_code=status,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            **(
                {"Retry-After": str(retry_after or (60 if status == 429 else 5))}
                if retryable
                else {}
            ),
        },
    )


async def domain_error(request: Request, error: DomainError) -> JSONResponse:
    # Application errors carry canonical metadata in DomainError.details. Never
    # serialize the remaining details: they may contain provider payloads or PII.
    status = STATUS.get(error.code)
    raw_category = error.details.get("category")
    try:
        category = ErrorCategory(raw_category) if raw_category is not None else None
    except (ValueError, TypeError):
        category = None
    if category is None:
        if status in (401, 403):
            category = ErrorCategory.AUTHORIZATION
        elif error.code == "artifact_integrity_failure":
            category = ErrorCategory.VALIDATION
        elif error.code == "evaluation_failed":
            category = ErrorCategory.EVALUATION
        elif isinstance(error, PersistenceError) or error.code in RETRYABLE_CONFLICTS:
            category = ErrorCategory.PERSISTENCE
    if status is None:
        status = 422 if category in (ErrorCategory.VALIDATION, ErrorCategory.DOMAIN) else 503
        if category == ErrorCategory.AUTHORIZATION:
            status = 403
    retryable = error.details.get("retryable")
    if not isinstance(retryable, bool):
        retryable = status in (429, 503) or error.code in RETRYABLE_CONFLICTS
    delay = error.details.get("retry_after_seconds")
    retry_after = min(3600, max(1, delay)) if type(delay) is int else None
    return error_response(
        error.code, status, category=category, retryable=retryable, retry_after=retry_after
    )
