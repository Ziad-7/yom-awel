"""POST /submissions/{id}/questions: owner-only, validated, budgeted, and always answered."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.transport.support import (
    CSRF,
    DUPLICATES_CSV,
    browser,
    onboard,
    settings_for,
    start,
    submit,
)
from yom_awel.transport.app import create_app


@pytest.fixture
def graded(tmp_path):
    with TestClient(create_app(settings_for(tmp_path)), headers=CSRF) as client:
        onboard(client, "Sara", "en")
        start(client)
        outcome, _, _ = submit(client, DUPLICATES_CSV, "dup")
        yield client, outcome["submission_id"]


def ask(
    client: TestClient, submission_id: str, question: str = "What should I fix first?", **extra
):
    return client.post(
        f"/api/v1/submissions/{submission_id}/questions",
        json={"question": question, "language": "en", **extra},
    )


def test_without_gemini_the_guide_answers_from_the_learners_own_results(graded):
    client, submission_id = graded
    body = ask(client, submission_id).json()

    assert body["source"] == "guide"
    assert body["language"] == "en"
    assert "Unique orders failed" in body["answer"]
    assert any("Spreadsheet row" in fact for fact in body["grounded_on"])


def test_only_the_owner_can_ask_and_input_is_validated(graded):
    client, submission_id = graded
    other = browser(client.app)
    onboard(other, "Mona")

    assert ask(other, submission_id).status_code == 404
    assert ask(client, str(uuid4())).status_code == 404
    assert ask(client, submission_id, "").status_code == 422
    assert ask(client, submission_id, "x" * 301).status_code == 422
    assert ask(client, submission_id, extra="field").status_code == 422
    no_csrf = TestClient(client.app, cookies=client.cookies)
    assert ask(no_csrf, submission_id).status_code == 403


def test_questions_have_their_own_per_learner_budget(graded):
    client, submission_id = graded
    statuses = [ask(client, submission_id).status_code for _ in range(11)]
    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429
    assert client.get("/api/v1/tasks").status_code == 200
