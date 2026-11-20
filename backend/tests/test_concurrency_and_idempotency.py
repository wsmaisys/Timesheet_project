import pytest

from apps.approvals.models import ApprovalEvent

from .conftest import auth_headers


@pytest.mark.django_db
def test_optimistic_concurrency_if_match_and_version_conflict(
    api_client,
    employee_user,
    approver_user,
    active_project,
    active_task,
    active_assignment,
    week_bounds,
):
    period_start, period_end = week_bounds
    ts_res = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end},
        format="json",
        **auth_headers(employee_user),
    )
    ts_id = ts_res.data["id"]
    initial_etag = ts_res["ETag"]
    assert ts_res.data["version"] == 1

    # Add entry advances version from 1 -> 2
    api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 180,
            "billable": True,
            "description": "SAP FI design workshop.",
        },
        format="json",
        **auth_headers(employee_user),
    )

    # Stale If-Match rejected with 409 TS_STATE_CONFLICT
    stale_patch = api_client.patch(
        f"/api/v1/timesheets/{ts_id}",
        {"notes": "Stale note"},
        format="json",
        **auth_headers(employee_user, HTTP_IF_MATCH=initial_etag),
    )
    assert stale_patch.status_code == 409
    assert stale_patch.data["error"]["code"] == "TS_STATE_CONFLICT"

    # Submit without stale version succeeds
    sub = api_client.post(
        f"/api/v1/timesheets/{ts_id}/submit",
        {"version": 2},
        format="json",
        **auth_headers(employee_user),
    )
    assert sub.status_code == 200
    assert sub.data["version"] == 3

    # Duplicate approval attempt (simulating second approver acting after first wins)
    app1 = api_client.post(
        f"/api/v1/timesheets/{ts_id}/approve",
        {"version": 3},
        format="json",
        **auth_headers(approver_user),
    )
    assert app1.status_code == 200

    app2 = api_client.post(
        f"/api/v1/timesheets/{ts_id}/approve",
        {},
        format="json",
        **auth_headers(approver_user),
    )
    assert app2.status_code == 409
    assert app2.data["error"]["code"] == "TS_NOT_SUBMITTED"
    assert ApprovalEvent.objects.filter(timesheet_id=ts_id, action="APPROVED").count() == 1


@pytest.mark.django_db
def test_idempotency_key_replay_and_payload_mismatch(
    api_client,
    employee_user,
    week_bounds,
):
    period_start, period_end = week_bounds
    key = "idem-create-ts-001"

    r1 = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end, "notes": "First call"},
        format="json",
        **auth_headers(employee_user, HTTP_IDEMPOTENCY_KEY=key),
    )
    assert r1.status_code == 201

    # Exact retry returns cached 201 without raising TS_PERIOD_EXISTS
    r2 = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end, "notes": "First call"},
        format="json",
        **auth_headers(employee_user, HTTP_IDEMPOTENCY_KEY=key),
    )
    assert r2.status_code == 201
    assert r2.data["id"] == r1.data["id"]
    assert r2["X-Idempotent-Replay"] == "true"

    # Reusing same key with different payload fails with 409 TS_STATE_CONFLICT
    r3 = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end, "notes": "Different body"},
        format="json",
        **auth_headers(employee_user, HTTP_IDEMPOTENCY_KEY=key),
    )
    assert r3.status_code == 409
    assert r3.data["error"]["code"] == "TS_STATE_CONFLICT"
