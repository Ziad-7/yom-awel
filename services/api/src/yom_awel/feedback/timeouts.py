import math

MAX_PROVIDER_TIMEOUT_SECONDS = 10.0


def validate_timeout_seconds(value: float) -> float:
    """Reject disabled/invalid deadlines before clamping a valid positive budget."""
    if not math.isfinite(value) or value <= 0:
        raise ValueError("timeout_seconds must be a finite positive number")
    return min(value, MAX_PROVIDER_TIMEOUT_SECONDS)
