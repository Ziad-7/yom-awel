import hashlib
import hmac
import math
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from json import JSONDecodeError
from typing import Annotated, Literal
from uuid import UUID, uuid4

import jwt
from fastapi import Cookie, Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from yom_awel.application.commands import CreateUploadCommand, ProcessSubmissionCommand
from yom_awel.application.models import (
    CurrentTaskResult,
    ProcessingState,
    UploadAuthorizationResult,
    UploadCompletionResult,
)
from yom_awel.domain.contracts import (
    ApplicationError,
    FeedbackResult,
    SkillsProfile,
    SubmissionOutcome,
)
from yom_awel.domain.entities import Artifact, Learner
from yom_awel.domain.enums import Channel, Language
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import dataset
from yom_awel.transport.artifact_validation import validate_content, validate_metadata
from yom_awel.transport.auth import SESSION_COOKIE, SESSION_SECONDS, Authenticator, Identity
from yom_awel.transport.dependencies import Services, compose
from yom_awel.transport.errors import domain_error, error_response
from yom_awel.transport.models import (
    AttemptResult,
    HealthResult,
    LanguageInput,
    OnboardInput,
    RuntimeResult,
    SessionResult,
    SubmissionInput,
    TaskDetail,
    TaskList,
    UploadInput,
)
from yom_awel.transport.settings import Settings

MAX_BYTES = 5 * 1024 * 1024
CSRF_HEADER = "x-yom-awel"
# Telegram authenticates with its own secret header and cannot send the CSRF header.
CSRF_EXEMPT = frozenset({"/api/v1/telegram/webhook"})


def validate_file(body: UploadInput) -> None:
    validate_metadata(body.filename, body.content_type)


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    config.validate()
    auth = Authenticator(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.services is None:
            app.state.services = compose(config)
        await app.state.services.seed_tasks()
        yield

    app = FastAPI(
        title="Yom Awel API",
        version="1.0.0",
        lifespan=lifespan,
        responses={
            status: {"model": ApplicationError, "description": description}
            for status, description in {
                400: "Malformed request",
                401: "Authentication required",
                403: "Access denied",
                404: "Resource not found",
                409: "State or idempotency conflict",
                413: "Artifact too large",
                415: "Unsupported or unsafe artifact",
                422: "Validation or artifact integrity failure",
                429: "Rate limit exceeded",
                503: "Evaluation, persistence or infrastructure unavailable",
            }.items()
        },
    )
    app.state.services = services
    app.state.settings = config
    app.state.auth = auth
    buckets: dict[str, deque[float]] = defaultdict(deque)

    def limit(key: str) -> None:
        now = time.monotonic()
        if len(buckets) > 10000:
            for stale in list(buckets):
                if not buckets[stale] or buckets[stale][-1] < now - 60:
                    del buckets[stale]
            if len(buckets) > 10000 and key not in buckets:
                raise DomainError("rate_limited", "Rate limit reached")
        bucket = buckets[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= config.rate_limit:
            raise DomainError("rate_limited", "Rate limit reached")
        bucket.append(now)

    @app.middleware("http")
    async def boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        try:
            limit("request:" + (request.client.host if request.client else "unknown"))
        except DomainError:
            return error_response("rate_limited", 429)
        if (
            request.method in ("POST", "PUT", "PATCH", "DELETE")
            and request.url.path not in CSRF_EXEMPT
            and request.headers.get(CSRF_HEADER) != "1"
        ):
            return error_response("forbidden", 403)
        if request.method in ("POST", "PUT", "PATCH"):
            maximum = MAX_BYTES if request.method == "PUT" else 65536
            try:
                if int(request.headers.get("content-length", "0")) > maximum:
                    return error_response("too_large", 413)
            except ValueError:
                return error_response("invalid_request", 400)
            # Buffer only bounded input, including chunked JSON. File uploads are bounded too.
            content = bytearray()
            async for chunk in request.stream():
                content.extend(chunk)
                if len(content) > maximum:
                    return error_response("too_large", 413)
            request._body = bytes(content)
        try:
            response = await call_next(request)
        except DomainError as error:
            return await domain_error(request, error)
        except Exception:  # noqa: BLE001 - redact unexpected transport/provider failures
            return error_response("unavailable", 503)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Upload-Token", "X-Yom-Awel"],
        expose_headers=["Retry-After"],
    )
    app.add_exception_handler(DomainError, domain_error)  # type: ignore[arg-type]

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response("invalid_request", 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response("invalid_request", exc.status_code)

    def service() -> Services:
        if app.state.services is None:
            raise DomainError("unavailable", "Services not ready")
        result: Services = app.state.services
        return result

    async def identity(
        yom_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> Identity:
        verified = auth.verify(yom_session)
        limit(verified.provider + ":" + verified.subject)
        return verified

    async def learner(who: Annotated[Identity, Depends(identity)]) -> Learner:
        return await service().learner(who)

    @app.get("/api/v1/health", response_model=HealthResult)
    async def health() -> HealthResult:
        return HealthResult()

    @app.get("/api/v1/runtime", response_model=RuntimeResult)
    async def runtime() -> RuntimeResult:
        return RuntimeResult(
            mode=config.mode,
            feedback_provider="gemini" if config.uses_gemini else "deterministic",
        )

    @app.post("/api/v1/auth/session", response_model=SessionResult)
    async def session(
        request: Request,
        response: Response,
        yom_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> SessionResult:
        limit("session:" + (request.client.host if request.client else "unknown"))
        try:
            auth.verify(yom_session)
        except DomainError:
            response.set_cookie(
                SESSION_COOKIE,
                auth.issue(),
                max_age=SESSION_SECONDS,
                httponly=True,
                secure=config.secure_cookies,
                samesite="lax",
                path="/",
            )
        return SessionResult(expires_in=SESSION_SECONDS)

    @app.post("/api/v1/auth/logout", status_code=204)
    async def logout(response: Response) -> Response:
        response.status_code = 204
        response.delete_cookie(
            SESSION_COOKIE,
            httponly=True,
            secure=config.secure_cookies,
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/api/v1/learners/onboard", response_model=Learner)
    async def onboard(body: OnboardInput, who: Annotated[Identity, Depends(identity)]) -> Learner:
        return await service().onboard(who, body)

    @app.get("/api/v1/learners/me", response_model=Learner)
    async def me(user: Annotated[Learner, Depends(learner)]) -> Learner:
        return user

    @app.put("/api/v1/learners/me/language", response_model=Learner)
    async def language(body: LanguageInput, user: Annotated[Learner, Depends(learner)]) -> Learner:
        return await service().language.execute(user.learner_id, body.preferred_language)

    @app.get("/api/v1/tasks", response_model=TaskList)
    async def tasks(user: Annotated[Learner, Depends(learner)]) -> TaskList:
        return await service().task_list(user.learner_id)

    @app.get("/api/v1/tasks/current", response_model=CurrentTaskResult)
    async def current(user: Annotated[Learner, Depends(learner)]) -> CurrentTaskResult:
        return await service().tasks.execute(user.learner_id)

    @app.get("/api/v1/skills", response_model=SkillsProfile)
    async def skills(user: Annotated[Learner, Depends(learner)]) -> SkillsProfile:
        return await service().skills.execute(user.learner_id)

    @app.get("/api/v1/attempts", response_model=list[AttemptResult])
    async def attempts(user: Annotated[Learner, Depends(learner)]) -> list[AttemptResult]:
        return await service().history(user.learner_id)

    @app.get("/api/v1/tasks/{task_id}", response_model=TaskDetail)
    async def task_detail(task_id: str, user: Annotated[Learner, Depends(learner)]) -> TaskDetail:
        return service().task_detail(task_id)

    @app.post("/api/v1/tasks/{task_id}/start", response_model=CurrentTaskResult)
    async def start(task_id: str, user: Annotated[Learner, Depends(learner)]) -> CurrentTaskResult:
        return await service().start.execute(user.learner_id, task_id)

    @app.get(
        "/api/v1/tasks/{task_id}/dataset",
        response_class=Response,
        responses={200: {"content": {"text/csv": {}, "application/octet-stream": {}}}},
    )
    async def download(
        task_id: str,
        user: Annotated[Learner, Depends(learner)],
        file_format: Annotated[Literal["csv", "xlsx"], Query(alias="format")] = "csv",
    ) -> Response:
        file = dataset(service().catalog.get(task_id), file_format)
        return Response(
            file.content,
            media_type=file.media_type,
            headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
        )

    @app.post("/api/v1/artifacts/upload-authorization", response_model=UploadAuthorizationResult)
    async def authorize(
        body: UploadInput, user: Annotated[Learner, Depends(learner)]
    ) -> UploadAuthorizationResult:
        validate_file(body)
        result = await service().uploads.execute(
            CreateUploadCommand(
                learner_id=user.learner_id,
                filename=body.filename,
                size_bytes=body.size_bytes,
                artifact_sha256=body.artifact_sha256,
            )
        )
        artifact = Artifact(
            artifact_id=result.artifact_id,
            learner_id=user.learner_id,
            filename=body.filename,
            size_bytes=body.size_bytes,
            sha256=body.artifact_sha256,
        )
        token = jwt.encode(
            {
                "artifact": artifact.model_dump(mode="json"),
                "content_type": body.content_type,
                "aud": "artifact-upload",
                "exp": datetime.now(UTC) + timedelta(seconds=300),
            },
            config.secret,
            algorithm="HS256",
        )
        return result.model_copy(
            update={
                "upload_url": f"/api/v1/artifacts/{result.artifact_id}/content",
                "upload_token": token,
                "headers": {"X-Upload-Token": token, "Content-Type": body.content_type},
            }
        )

    @app.put("/api/v1/artifacts/{artifact_id}/content", response_model=UploadCompletionResult)
    async def upload(
        artifact_id: UUID,
        request: Request,
        user: Annotated[Learner, Depends(learner)],
        x_upload_token: Annotated[str | None, Header()] = None,
    ) -> UploadCompletionResult:
        try:
            claims = jwt.decode(
                x_upload_token or "",
                config.secret,
                algorithms=["HS256"],
                audience="artifact-upload",
                options={"require": ["exp", "aud", "artifact", "content_type"]},
            )
            artifact = Artifact.model_validate(claims["artifact"])
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise DomainError("forbidden", "Upload authorization invalid") from exc
        if artifact.learner_id != user.learner_id or artifact.artifact_id != artifact_id:
            raise DomainError("forbidden", "Upload authorization invalid")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != claims["content_type"]:
            raise DomainError("artifact_type_mismatch", "Upload MIME does not match authorization")
        content = await request.body()
        if (
            len(content) != artifact.size_bytes
            or hashlib.sha256(content).hexdigest() != artifact.sha256
        ):
            raise DomainError("artifact_integrity_failure", "Upload does not match authorization")
        validate_content(artifact.filename, content_type, content)
        async with service().factory() as uow:
            existing = await uow.artifacts.get(artifact_id, user.learner_id)
            if existing is None:
                await uow.artifacts.put(artifact, content)
            elif existing != artifact:
                raise DomainError("forbidden", "Artifact mismatch")
            await uow.commit()
        return await service().completion.execute(user.learner_id, artifact_id)

    @app.post("/api/v1/artifacts/{artifact_id}/complete", response_model=UploadCompletionResult)
    async def complete(
        artifact_id: UUID, user: Annotated[Learner, Depends(learner)]
    ) -> UploadCompletionResult:
        return await service().completion.execute(user.learner_id, artifact_id)

    @app.post("/api/v1/submissions", response_model=SubmissionOutcome | ProcessingState)
    async def submit(
        body: SubmissionInput,
        response: Response,
        user: Annotated[Learner, Depends(learner)],
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    ) -> SubmissionOutcome | ProcessingState:
        result = await service().submissions.execute(
            ProcessSubmissionCommand(
                learner_id=user.learner_id,
                channel=Channel.WEB,
                idempotency_key=idempotency_key,
                **body.model_dump(),
            ),
            str(uuid4()),
        )
        if isinstance(result, ProcessingState):
            response.status_code = 202
            response.headers["Retry-After"] = str(result.retry_after_seconds)
        return result

    @app.get(
        "/api/v1/submissions/{submission_id}", response_model=SubmissionOutcome | ProcessingState
    )
    async def outcome(
        submission_id: UUID,
        response: Response,
        user: Annotated[Learner, Depends(learner)],
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    ) -> SubmissionOutcome | ProcessingState:
        # Member2's lookup port is keyed by learner + idempotency key, never a global ID.
        async with service().factory() as uow:
            reservation = await uow.submissions.get_reservation(user.learner_id, idempotency_key)
        if reservation is None or reservation.submission_id != submission_id:
            raise DomainError("not_found", "Submission not found")
        if reservation.outcome:
            return reservation.outcome
        retry = max(
            1,
            min(
                3600, math.ceil((reservation.lease_expires_at - datetime.now(UTC)).total_seconds())
            ),
        )
        response.status_code = 202
        response.headers["Retry-After"] = str(retry)
        return ProcessingState(
            submission_id=submission_id, status=reservation.status, retry_after_seconds=retry
        )

    @app.get("/api/v1/submissions/{submission_id}/feedback", response_model=FeedbackResult)
    async def feedback(
        submission_id: UUID,
        language: Language,
        user: Annotated[Learner, Depends(learner)],
    ) -> FeedbackResult:
        return await service().feedback_in(user.learner_id, submission_id, language)

    @app.post("/api/v1/telegram/webhook", response_model=dict[str, bool])
    async def telegram(
        request: Request, x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None
    ) -> Response:
        if not config.telegram_secret or not hmac.compare_digest(
            x_telegram_bot_api_secret_token or "", config.telegram_secret
        ):
            raise DomainError("unauthorized", "Webhook authentication required")
        from yom_awel.transport.telegram import TelegramAdapter, TelegramClient

        try:
            update = await request.json()
        except (JSONDecodeError, UnicodeDecodeError):
            return error_response("invalid_request", 400)
        if not isinstance(update, dict):
            return error_response("invalid_request", 400)
        client = getattr(app.state, "telegram_client", None) or TelegramClient(
            config.telegram_token
        )
        adapter = TelegramAdapter(service(), client)
        try:
            await adapter.handle(update)
        except DomainError as error:
            return await domain_error(request, error)
        return JSONResponse({"ok": True})

    return app
