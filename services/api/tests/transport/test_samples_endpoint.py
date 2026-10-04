"""Judge mode: sample submissions are opt-in, learner-only, and go through the real pipeline."""

import pytest
from fastapi.testclient import TestClient

from tests.transport.support import CSRF, onboard, settings_for, submit
from yom_awel.transport.app import create_app


def client_for(tmp_path, **overrides):
    client = TestClient(create_app(settings_for(tmp_path, **overrides)), headers=CSRF)
    client.__enter__()
    onboard(client)
    return client


@pytest.fixture
def judge(tmp_path):
    client = client_for(tmp_path, demo_samples=True)
    yield client
    client.__exit__(None, None, None)


def test_samples_are_off_unless_enabled(tmp_path):
    client = client_for(tmp_path)
    try:
        assert client.get("/api/v1/runtime").json()["demo_samples"] is False
        assert client.get("/api/v1/tasks/clean-sales/samples").status_code == 404
        assert client.get("/api/v1/tasks/clean-sales/samples/fully_cleaned").status_code == 404
    finally:
        client.__exit__(None, None, None)


def test_listed_samples_name_their_tested_result(judge):
    assert judge.get("/api/v1/runtime").json()["demo_samples"] is True
    listed = judge.get("/api/v1/tasks/clean-sales/samples").json()["samples"]

    assert [item["sample_id"] for item in listed] == [
        "duplicates_left",
        "half_done_excel",
        "column_deleted",
        "fully_cleaned",
    ]
    assert listed[0] == {
        "sample_id": "duplicates_left",
        "filename": "sales_retry_duplicates.csv",
        "outcome": "retry",
        "score": 75,
    }


@pytest.mark.parametrize(
    ("task_id", "sample_id", "mime"),
    [
        ("clean-sales", "duplicates_left", "text/csv"),
        (
            "clean-sales",
            "fully_cleaned",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        ("sql-report", "hard_coded", "text/plain"),
        ("client-email", "wrong_date_reply", "text/plain"),
    ],
)
def test_a_downloaded_sample_grades_as_listed_through_the_upload_pipeline(
    judge, task_id, sample_id, mime
):
    assert judge.post(f"/api/v1/tasks/{task_id}/start").status_code == 200
    listed = {
        item["sample_id"]: item
        for item in judge.get(f"/api/v1/tasks/{task_id}/samples").json()["samples"]
    }
    download = judge.get(f"/api/v1/tasks/{task_id}/samples/{sample_id}")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(mime)
    assert download.headers["cache-control"] == "no-store"
    item = listed[sample_id]
    assert f'filename="{item["filename"]}"' in download.headers["content-disposition"]

    outcome, _, _ = submit(judge, download.content, sample_id, item["filename"], mime)

    evaluation = outcome["evaluation"]
    assert (evaluation["passed"], evaluation["score"]) == (item["outcome"] == "pass", item["score"])


def test_unknown_or_malformed_samples_and_anonymous_visitors_are_refused(judge):
    assert judge.get("/api/v1/tasks/clean-sales/samples/nope").status_code == 404
    assert judge.get("/api/v1/tasks/no-such-task/samples").status_code == 404
    assert judge.get("/api/v1/tasks/clean-sales/samples/..%2Ftask.json").status_code in (404, 422)
    assert judge.get("/api/v1/tasks/clean-sales/samples/Bad-Id").status_code == 422
    anonymous = TestClient(judge.app)
    assert anonymous.get("/api/v1/tasks/clean-sales/samples").status_code == 401
    assert anonymous.get("/api/v1/tasks/clean-sales/samples/fully_cleaned").status_code == 401
