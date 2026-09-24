import pytest

from yom_awel.feedback.errors import ProviderResponseError


def test_provider_error_allows_traceback_assignment_during_propagation() -> None:
    error = ProviderResponseError("malformed_response")
    with pytest.raises(ProviderResponseError) as caught:
        raise error from ValueError("invalid provider payload")
    caught.value.__traceback__ = caught.value.__traceback__
    assert isinstance(caught.value.__cause__, ValueError)
