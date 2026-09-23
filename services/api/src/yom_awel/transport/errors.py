from fastapi import Request
from fastapi.responses import JSONResponse

from yom_awel.domain.contracts import ApplicationError
from yom_awel.domain.enums import ErrorCategory
from yom_awel.domain.errors import DomainError

STATUS = {
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
    "too_large": 413,
    "unsupported_artifact": 415,
    "rate_limited": 429,
    "unavailable": 503,
    "supabase_provider_error": 503,
}


def error_response(code: str, status: int) -> JSONResponse:
    category = ErrorCategory.AUTHORIZATION if status in (401, 403) else ErrorCategory.VALIDATION
    if status >= 500:
        category = ErrorCategory.INFRASTRUCTURE
    message = "تعذّر إكمال الطلب. راجع البيانات وحاول تاني."
    if status == 401:
        message = "الجلسة انتهت. ابدأ جلسة جديدة."
    error = ApplicationError(
        code=code, category=category, message=message, retryable=status in (429, 503)
    )
    return JSONResponse(
        error.model_dump(mode="json"),
        status_code=status,
        headers={"Retry-After": "60"} if status == 429 else {},
    )


async def domain_error(request: Request, error: DomainError) -> JSONResponse:
    return error_response(error.code, STATUS.get(error.code, 422))
