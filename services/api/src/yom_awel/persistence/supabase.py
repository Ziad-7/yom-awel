"""Typed, cloud-free boundary for the Supabase submission RPCs.

The application never receives a Supabase service key.  A deployment injects a
small server-side client implementing the protocols below; tests can provide a
transport that records calls without importing the Supabase SDK.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import NAMESPACE_OID, UUID, uuid4, uuid5

from pydantic import ValidationError

from yom_awel.domain.contracts import SubmissionOutcome
from yom_awel.domain.entities import SubmissionReservation
from yom_awel.domain.enums import Channel, SubmissionStatus
from yom_awel.domain.errors import IdempotencyConflict, PersistenceError
from yom_awel.ports.repositories import MAX_SUBMISSION_LEASE_SECONDS


class SupabasePersistenceError(PersistenceError):
    """Stable, sanitized errors raised at the external provider boundary."""

    def __init__(self, code: str, message: str = "Supabase persistence operation failed") -> None:
        super().__init__(code, message)


class SupabaseResponse(Protocol):
    data: object
    error: object | None


class SupabaseRpcClient(Protocol):
    async def rpc(self, function: str, params: Mapping[str, object]) -> SupabaseResponse: ...


class SupabaseQueryClient(Protocol):
    async def select_one(
        self, table: str, filters: Mapping[str, object]
    ) -> Mapping[str, object] | None: ...


def _response_value(response: SupabaseResponse) -> object:
    if response.error is not None:
        if _is_idempotency_conflict(response.error):
            # Preserve a stable domain signal while discarding provider text.
            raise SupabasePersistenceError("idempotency_conflict")
        # Provider details are deliberately not copied into a user-visible error.
        raise SupabasePersistenceError("supabase_provider_error")
    return response.data


def _is_idempotency_conflict(error: object) -> bool:
    if not isinstance(error, Mapping):
        return False
    return any(str(error.get(field)) in {"23505", "409"} for field in ("code", "status"))


def _row(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], Mapping):
        return cast(Mapping[str, object], value[0])
    raise SupabasePersistenceError("provider_payload_invalid", "Provider returned no row")


_SUBMISSION_KEYS = {
    "reservation_id",
    "submission_id",
    "learner_id",
    "task_version_id",
    "artifact_id",
    "channel",
    "idempotency_key",
    "request_fingerprint",
    "status",
    "created_at",
    "updated_at",
    "version",
    "lease_expires_at",
    "lease_owner",
    "outcome",
}


def map_submission_row(value: object) -> SubmissionReservation:
    """Map one RPC row and reject null, unknown, or malformed provider data."""

    row = _row(value)
    if set(row) != _SUBMISSION_KEYS:
        raise SupabasePersistenceError("provider_payload_invalid", "Unexpected submission columns")
    if any(row[key] is None for key in _SUBMISSION_KEYS - {"lease_owner", "outcome"}):
        raise SupabasePersistenceError(
            "provider_payload_invalid", "Required submission value is null"
        )
    try:
        return SubmissionReservation.model_validate(
            {key: row[key] for key in _SUBMISSION_KEYS if key != "updated_at"}
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise SupabasePersistenceError(
            "provider_payload_invalid", "Invalid submission row"
        ) from exc


def _json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SupabaseSubmissionRepository:
    """Submission port backed by the two atomic server-side RPCs.

    Reserve and finalize are separate network calls by design.  Evaluation and
    feedback run outside this adapter and therefore never hold a database
    transaction open.
    """

    def __init__(
        self,
        rpc: SupabaseRpcClient,
        query: SupabaseQueryClient | None = None,
        *,
        clock: Any | None = None,
    ) -> None:
        self._rpc = rpc
        self._query = query
        self._clock = clock
        self._reservations: dict[UUID, SubmissionReservation] = {}

    async def reserve(
        self,
        learner_id: UUID,
        task_version_id: UUID,
        artifact_id: UUID,
        channel: Channel,
        key: str,
        request_fingerprint: str,
        lease_seconds: int,
        lease_owner: str,
    ) -> SubmissionReservation:
        if (
            lease_seconds <= 0
            or lease_seconds > MAX_SUBMISSION_LEASE_SECONDS
            or not lease_owner.strip()
        ):
            raise ValueError(
                "lease_seconds must be between 1 and 3600 and lease_owner must be non-empty"
            )
        params: dict[str, object] = {
            "p_learner_id": str(learner_id),
            "p_task_version_id": str(task_version_id),
            "p_artifact_id": str(artifact_id),
            "p_channel": channel.value,
            "p_idempotency_key": key,
            "p_request_fingerprint": request_fingerprint,
            "p_lease_seconds": lease_seconds,
            "p_lease_owner": lease_owner,
        }
        try:
            response = await self._rpc.rpc("reserve_submission", params)
            reservation = map_submission_row(_response_value(response))
        except SupabasePersistenceError as exc:
            if exc.code == "idempotency_conflict":
                raise IdempotencyConflict(key) from None
            raise
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc
        self._reservations[reservation.reservation_id] = reservation
        return reservation

    async def get_reservation(self, learner_id: UUID, key: str) -> SubmissionReservation | None:
        if self._query is None:
            raise SupabasePersistenceError("query_client_required")
        try:
            value = await self._query.select_one(
                "submissions", {"learner_id": str(learner_id), "idempotency_key": key}
            )
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc
        if value is None:
            return None
        reservation = map_submission_row(value)
        if reservation.learner_id != learner_id:
            raise SupabasePersistenceError("provider_payload_invalid", "Learner scope mismatch")
        return reservation

    async def expire(
        self,
        learner_id: UUID,
        key: str,
        expected_version: int | None = None,
        lease_owner: str | None = None,
    ) -> None:
        if expected_version is None or lease_owner is None or not lease_owner:
            raise SupabasePersistenceError("lease_release_requires_cas")
        params: dict[str, object] = {
            "p_learner_id": str(learner_id),
            "p_idempotency_key": key,
            "p_expected_version": expected_version,
            "p_lease_owner": lease_owner,
        }
        try:
            response = await self._rpc.rpc("expire_submission", params)
            _response_value(response)
        except SupabasePersistenceError:
            raise
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc

    async def finalize(
        self,
        reservation_id: UUID,
        expected_version: int,
        lease_owner: str,
        outcome: SubmissionOutcome,
    ) -> None:
        reservation = await self._load_reservation(reservation_id)
        if reservation.lease_owner != lease_owner:
            raise SupabasePersistenceError("reservation_owner_conflict")
        if reservation.version != expected_version:
            raise SupabasePersistenceError("reservation_version_conflict")
        if reservation.status == SubmissionStatus.COMPLETED:
            raise SupabasePersistenceError("reservation_already_finalized")
        if reservation.lease_expires_at <= (
            datetime.now(UTC) if self._clock is None else self._clock.now()
        ):
            raise SupabasePersistenceError("reservation_expired")
        if outcome.submission_id != reservation.submission_id:
            raise SupabasePersistenceError("submission_mismatch")
        if outcome.evaluation.task_version_id != reservation.task_version_id:
            raise SupabasePersistenceError("task_version_mismatch")
        now = datetime.now(UTC) if self._clock is None else self._clock.now()
        evaluation_id = uuid4()
        feedback_id = uuid4()
        event_id = uuid4()
        attempt = {
            "attempt_id": str(outcome.attempt_id),
            "attempt_number": outcome.attempt_number,
            "started_at": reservation.created_at.isoformat(),
            "completed_at": now.isoformat(),
        }
        evaluation = outcome.evaluation.model_dump(mode="json")
        evaluation["evaluation_id"] = str(evaluation_id)
        feedback = outcome.feedback.model_dump(mode="json")
        feedback["feedback_id"] = str(feedback_id)
        progress_expected_version = await self._progress_version(reservation.learner_id)
        evidence = await self._skill_evidence(reservation.task_version_id, outcome, now)
        params: dict[str, object] = {
            "p_reservation_id": str(reservation_id),
            "p_expected_version": expected_version,
            "p_lease_owner": lease_owner,
            "p_evaluation": _json(evaluation),
            "p_feedback": _json(feedback),
            "p_attempt": _json(attempt),
            "p_evidence": evidence,
            "p_progress_status": outcome.learner_status.value,
            "p_progress_expected_version": progress_expected_version,
            "p_outbox": {
                "event_id": str(event_id),
                "event_type": "submission.processed",
                "payload": {
                    "submission_id": str(outcome.submission_id),
                    "passed": outcome.evaluation.passed,
                },
            },
            "p_outcome": _json(outcome.model_dump(mode="json")),
        }
        try:
            response = await self._rpc.rpc("finalize_submission", params)
            completed = map_submission_row(_response_value(response))
        except SupabasePersistenceError:
            raise
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc
        self._reservations[reservation_id] = completed

    async def _load_reservation(self, reservation_id: UUID) -> SubmissionReservation:
        if self._query is None:
            raise SupabasePersistenceError("query_client_required")
        try:
            value = await self._query.select_one(
                "submissions", {"reservation_id": str(reservation_id)}
            )
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc
        if value is None:
            raise SupabasePersistenceError("reservation_not_loaded")
        reservation = map_submission_row(value)
        if reservation.reservation_id != reservation_id:
            raise SupabasePersistenceError("provider_payload_invalid")
        return reservation

    async def _skill_evidence(
        self, task_version_id: UUID, outcome: SubmissionOutcome, recorded_at: datetime
    ) -> list[dict[str, object]]:
        if not outcome.evaluation.passed:
            return []
        if self._query is None:
            raise SupabasePersistenceError("query_client_required")
        try:
            value = await self._query.select_one(
                "task_versions", {"task_version_id": str(task_version_id)}
            )
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc
        if value is None or value.get("task_version_id") != str(task_version_id):
            raise SupabasePersistenceError("provider_payload_invalid", "Invalid task version row")
        mappings = value.get("skill_mappings")
        if not isinstance(mappings, list):
            raise SupabasePersistenceError("provider_payload_invalid", "Invalid skill mappings")
        passed_check_ids = {check.check_id for check in outcome.evaluation.checks if check.passed}
        evidence: list[dict[str, object]] = []
        for mapping in mappings:
            if not isinstance(mapping, Mapping):
                raise SupabasePersistenceError("provider_payload_invalid", "Invalid skill mapping")
            skill_id = mapping.get("skill_id")
            check_id = mapping.get("check_id")
            weight = mapping.get("weight")
            if (
                not isinstance(skill_id, str)
                or not isinstance(check_id, str)
                or type(weight) is not int
                or weight < 0
            ):
                raise SupabasePersistenceError("provider_payload_invalid", "Invalid skill mapping")
            if check_id in passed_check_ids and weight > 0:
                evidence.append(
                    {
                        "evidence_id": str(
                            uuid5(
                                NAMESPACE_OID,
                                f"{outcome.attempt_id}:{task_version_id}:{skill_id}:{check_id}",
                            )
                        ),
                        "skill_id": skill_id,
                        "check_id": check_id,
                        "awarded_points": weight,
                        "available_points": weight,
                        "recorded_at": recorded_at.isoformat(),
                    }
                )
        return evidence

    async def _progress_version(self, learner_id: UUID) -> int:
        if self._query is None:
            raise SupabasePersistenceError("query_client_required")
        try:
            value = await self._query.select_one(
                "learner_progress", {"learner_id": str(learner_id)}
            )
        except Exception as exc:
            raise SupabasePersistenceError("supabase_provider_error") from exc
        if value is None or set(value) != {
            "learner_id",
            "current_status",
            "current_task_id",
            "version",
            "updated_at",
            "reset_at",
        }:
            raise SupabasePersistenceError("provider_payload_invalid", "Invalid progress row")
        version = value.get("version")
        if type(version) is not int or version < 1:
            raise SupabasePersistenceError("provider_payload_invalid", "Invalid progress version")
        return version
