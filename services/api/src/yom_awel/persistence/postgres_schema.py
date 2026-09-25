"""Idempotent DDL for the hosted Postgres adapter.

Tables mirror the SQLite adapter one to one, with native Postgres types:
uuid keys, timestamptz instants, jsonb documents and bytea artifact content.
Every statement is static; the schema name is applied through the
transaction-local search_path, never interpolated into SQL text.
"""

from __future__ import annotations

import re
from typing import LiteralString

# Serializes schema creation across concurrent cold starts. The value is an
# arbitrary constant private to this adapter ("yomawel1" as ASCII).
SCHEMA_LOCK_KEY = 0x796F6D6177656C31
SCHEMA_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

TABLES: tuple[LiteralString, ...] = (
    """
    CREATE TABLE IF NOT EXISTS learners (
        learner_id uuid PRIMARY KEY,
        display_name text NOT NULL,
        preferred_language text NOT NULL CHECK (preferred_language IN ('ar-EG', 'en')),
        status text NOT NULL CHECK (status IN ('ONBOARDING', 'READY', 'IN_TASK', 'PROCESSING',
            'NEEDS_RETRY', 'TASK_COMPLETED', 'PROGRAM_COMPLETED')),
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL,
        state_machine_version text NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS external_identities (
        identity_id uuid PRIMARY KEY,
        learner_id uuid NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
        provider text NOT NULL,
        provider_subject text NOT NULL,
        UNIQUE (provider, provider_subject)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_versions (
        task_version_id uuid PRIMARY KEY,
        task_id text NOT NULL,
        version text NOT NULL,
        instructions_ar text NOT NULL,
        instructions_en text NOT NULL,
        artifact_schema jsonb NOT NULL,
        evaluator_id text NOT NULL,
        evaluator_version text NOT NULL,
        pass_threshold integer NOT NULL CHECK (pass_threshold BETWEEN 0 AND 100),
        skill_mappings jsonb NOT NULL,
        content_hash text NOT NULL CHECK (length(content_hash) = 64),
        UNIQUE (task_id, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id uuid PRIMARY KEY,
        learner_id uuid NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
        filename text NOT NULL,
        size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 0 AND 5242880),
        sha256 text NOT NULL CHECK (length(sha256) = 64),
        content bytea NOT NULL CHECK (octet_length(content) <= 5242880)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS submissions (
        reservation_id uuid PRIMARY KEY,
        submission_id uuid NOT NULL UNIQUE,
        learner_id uuid NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
        task_version_id uuid NOT NULL REFERENCES task_versions(task_version_id),
        artifact_id uuid NOT NULL REFERENCES artifacts(artifact_id),
        channel text NOT NULL CHECK (channel IN ('web', 'telegram')),
        idempotency_key text NOT NULL,
        request_fingerprint text NOT NULL,
        status text NOT NULL CHECK (status IN ('RECEIVED', 'EVALUATING', 'COMPLETED', 'FAILED')),
        created_at timestamptz NOT NULL,
        version integer NOT NULL CHECK (version >= 1),
        lease_expires_at timestamptz NOT NULL,
        lease_owner text,
        outcome jsonb,
        UNIQUE (learner_id, idempotency_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evaluation_results (
        evaluation_id uuid PRIMARY KEY,
        result jsonb NOT NULL,
        recorded_at timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback_results (
        feedback_id uuid PRIMARY KEY,
        result jsonb NOT NULL,
        recorded_at timestamptz NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attempts (
        attempt_id uuid PRIMARY KEY,
        learner_id uuid NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
        submission_id uuid NOT NULL REFERENCES submissions(submission_id),
        task_version_id uuid NOT NULL REFERENCES task_versions(task_version_id),
        attempt_number integer NOT NULL CHECK (attempt_number >= 1),
        evaluation_id uuid NOT NULL REFERENCES evaluation_results(evaluation_id),
        feedback_id uuid NOT NULL REFERENCES feedback_results(feedback_id),
        evaluator_id text NOT NULL,
        evaluator_version text NOT NULL,
        prompt_version text NOT NULL,
        started_at timestamptz NOT NULL,
        completed_at timestamptz,
        UNIQUE (learner_id, task_version_id, attempt_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skill_evidence (
        evidence_id uuid PRIMARY KEY,
        learner_id uuid NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
        attempt_id uuid NOT NULL REFERENCES attempts(attempt_id),
        task_version_id uuid NOT NULL REFERENCES task_versions(task_version_id),
        skill_id text NOT NULL,
        check_id text NOT NULL,
        awarded_points integer NOT NULL CHECK (awarded_points >= 0),
        available_points integer NOT NULL CHECK (available_points > 0),
        recorded_at timestamptz NOT NULL,
        UNIQUE (attempt_id, skill_id, check_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learner_progress (
        learner_id uuid PRIMARY KEY REFERENCES learners(learner_id) ON DELETE CASCADE,
        current_status text NOT NULL,
        current_task_id text,
        version integer NOT NULL CHECK (version >= 1),
        updated_at timestamptz NOT NULL,
        reset_at timestamptz
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS outbox_events (
        event_id uuid PRIMARY KEY,
        event_type text NOT NULL,
        aggregate_id uuid NOT NULL,
        payload jsonb NOT NULL,
        created_at timestamptz NOT NULL,
        published_at timestamptz
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_attempts_learner_task
        ON attempts (learner_id, task_version_id, attempt_number)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_outbox_pending
        ON outbox_events (published_at, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_skill_evidence_learner
        ON skill_evidence (learner_id)
    """,
)


def validate_schema_name(schema: str) -> str:
    """Accept only a plain lower-case identifier so search_path cannot be abused."""

    if not SCHEMA_NAME.fullmatch(schema) or schema.startswith("pg_"):
        raise ValueError("schema must be a lower-case identifier that does not start with pg_")
    return schema
