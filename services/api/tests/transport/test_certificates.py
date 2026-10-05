"""Skills certificates: live, tamper-evident, and public only to whoever holds the link."""

import base64
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from tests.transport.support import (
    CLEAN_CSV,
    CSRF,
    DUPLICATES_CSV,
    TEST_SECRET,
    browser,
    onboard,
    settings_for,
    start,
    submit,
)
from yom_awel.domain.errors import DomainError
from yom_awel.transport import certificates
from yom_awel.transport.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(settings_for(tmp_path)), headers=CSRF) as learner:
        onboard(learner, "Sara")
        yield learner


def test_tokens_round_trip_and_reject_any_edit_or_other_secret():
    learner_id = uuid4()
    token = certificates.issue(TEST_SECRET, learner_id)

    assert len(token) == certificates.TOKEN_LENGTH
    assert certificates.verify(TEST_SECRET, token) == learner_id
    flipped = token[:-1] + ("A" if token[-1] != "A" else "B")
    for forged in (flipped, certificates.issue("another-secret-" + "y" * 32, learner_id), "!" * 43):
        with pytest.raises(DomainError):
            certificates.verify(TEST_SECRET, forged)


def test_no_certificate_before_a_pass(client):
    start(client)
    submit(client, DUPLICATES_CSV, "retry")
    assert client.get("/api/v1/learners/me/certificate").status_code == 404


def test_a_pass_after_a_retry_is_certified_with_its_evidence(client):
    start(client)
    submit(client, DUPLICATES_CSV, "retry")
    submit(client, CLEAN_CSV, "pass")

    mine = client.get("/api/v1/learners/me/certificate").json()

    assert mine["display_name"] == "Sara"
    [task] = mine["tasks"]
    assert (task["task_id"], task["score"], task["attempts"]) == ("clean-sales", 100, 2)
    assert set(task["checks"]) == {
        "unique_orders",
        "standard_dates",
        "valid_numeric_values",
        "complete_customer_records",
    }
    skills = {skill["skill_id"]: skill["evidence"] for skill in mine["skills"]}
    assert "unique_orders" in skills["data_cleaning"]

    public = TestClient(client.app).get(f"/api/v1/certificates/{mine['token']}")
    assert public.status_code == 200
    assert "set-cookie" not in public.headers
    body = public.json()
    assert {key: value for key, value in body.items() if key != "verified_at"} == {
        key: value for key, value in mine.items() if key != "verified_at"
    }


def test_edited_or_borrowed_tokens_are_not_found(client):
    start(client)
    submit(client, CLEAN_CSV, "pass")
    token = client.get("/api/v1/learners/me/certificate").json()["token"]
    other = browser(client.app)
    other_id = onboard(other, "Mona")["learner_id"]
    raw = base64.urlsafe_b64decode(token + "=")
    borrowed = base64.urlsafe_b64encode(UUID(other_id).bytes + raw[16:]).rstrip(b"=").decode()
    anonymous = TestClient(client.app)

    assert anonymous.get(f"/api/v1/certificates/{borrowed}").status_code == 404
    assert anonymous.get(f"/api/v1/certificates/{token[:-2]}AA").status_code == 404
    assert anonymous.get("/api/v1/certificates/short").status_code == 422
    valid_but_no_pass = certificates.issue(TEST_SECRET, UUID(other_id))
    assert anonymous.get(f"/api/v1/certificates/{valid_but_no_pass}").status_code == 404
