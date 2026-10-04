"""GET /submissions/{id}/insights: owner-only explanations of a graded submission."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.transport.support import (
    CLEAN_CSV,
    CSRF,
    DUPLICATES_CSV,
    REPOSITORY_ROOT,
    browser,
    onboard,
    settings_for,
    start,
    submit,
)
from yom_awel.transport.app import create_app

EXAMPLES = REPOSITORY_ROOT / "task_packages"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(settings_for(tmp_path)), headers=CSRF) as browser_client:
        onboard(browser_client)
        yield browser_client


def insights(client: TestClient, submission_id: str):
    return client.get(f"/api/v1/submissions/{submission_id}/insights")


def test_duplicates_are_located_and_priced(client):
    start(client)
    outcome, _, _ = submit(client, DUPLICATES_CSV, "duplicates")

    body = insights(client, outcome["submission_id"]).json()

    assert body["kind"] == "table"
    assert [c["passed"] for c in body["checks"]] == [
        c["passed"] for c in outcome["evaluation"]["checks"]
    ]
    assert {issue["issue"] for issue in body["issues"]} == {"duplicate_order_id"}
    impact = {m["metric_id"]: float(m["value"]) for m in body["impact"]}
    assert impact["revenue_overstated"] > 0
    assert body["table"]["total_rows"] >= 40


def test_clean_submission_reports_zero_cost(client):
    start(client)
    outcome, _, _ = submit(client, CLEAN_CSV, "clean")

    body = insights(client, outcome["submission_id"]).json()

    assert body["issues"] == []
    assert {float(m["value"]) for m in body["impact"]} == {0.0}


def test_rejected_file_insights_name_the_rejection(client):
    start(client)
    outcome, _, _ = submit(client, b"order_id\nSO-1\n", "too-few")

    body = insights(client, outcome["submission_id"]).json()

    assert body["rejected_code"] == outcome["evaluation"]["errors"][0]["code"]
    assert body["table"] is None


@pytest.mark.parametrize(
    ("task_id", "example", "filename", "kind"),
    [
        ("sql-report", "sql-report/1/examples/pass.sql", "report.sql", "sql"),
        ("client-email", "client-email/1/examples/fail.en.txt", "email.txt", "email"),
    ],
)
def test_sql_and_email_insights_follow_their_task(client, task_id, example, filename, kind):
    assert client.post(f"/api/v1/tasks/{task_id}/start").status_code == 200
    content = (EXAMPLES / example).read_bytes()
    outcome, _, _ = submit(client, content, kind, filename, "text/plain")

    body = insights(client, outcome["submission_id"]).json()

    assert body["kind"] == kind
    assert [c["passed"] for c in body["checks"]] == [
        c["passed"] for c in outcome["evaluation"]["checks"]
    ]


def test_other_learners_and_unknown_submissions_are_not_found(client):
    start(client)
    outcome, _, _ = submit(client, DUPLICATES_CSV, "private")
    other = browser(client.app)
    onboard(other, "منى")

    assert insights(other, outcome["submission_id"]).status_code == 404
    assert insights(client, str(uuid4())).status_code == 404
    assert insights(client, "not-a-uuid").status_code == 422
    assert (
        TestClient(client.app)
        .get(f"/api/v1/submissions/{outcome['submission_id']}/insights")
        .status_code
        == 401
    )
