from enum import StrEnum


class LearnerStatus(StrEnum):
    ONBOARDING = "ONBOARDING"
    READY = "READY"
    IN_TASK = "IN_TASK"
    PROCESSING = "PROCESSING"
    NEEDS_RETRY = "NEEDS_RETRY"
    TASK_COMPLETED = "TASK_COMPLETED"
    PROGRAM_COMPLETED = "PROGRAM_COMPLETED"


class SubmissionStatus(StrEnum):
    RECEIVED = "RECEIVED"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class Language(StrEnum):
    AR_EG = "ar-EG"
    EN = "en"


class Channel(StrEnum):
    WEB = "web"
    TELEGRAM = "telegram"


class ErrorCategory(StrEnum):
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    EVALUATION = "evaluation"
    PROVIDER = "provider"
    PERSISTENCE = "persistence"
    EXTERNAL_CHANNEL = "external_channel"
    INFRASTRUCTURE = "infrastructure"
    DOMAIN = "domain"
