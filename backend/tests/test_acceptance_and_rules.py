from datetime import date

import pytest

from apps.approvals.models import ApprovalEvent
from apps.assignments.models import ProjectAssignment
from apps.audit.models import AuditEvent
from apps.projects.models import Task
from apps.timesheets.models import Timesheet

from .conftest import auth_headers


@pytest.mark.django_db
def test_ac01_ac02_ac03_full_happy_path_and_totals(
    api_client,
    employee_user,
    approver_user,
    active_project,
    active_task,
    active_assignment,
    week_bounds,
):
    period_start, period_end = week_bounds

    # Create weekly draft timesheet
    res = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end, "notes": "Sprint 4"},
        format="json",
        **auth_headers(employee_user),
    )
    assert res.status_code == 201
    ts_id = res.data["id"]
    assert res.data["status"] == "DRAFT"
    assert res.data["total_minutes"] == 0

    # AC-01: Add valid entry with integer minutes
    e1 = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 480,
            "billable": True,
            "description": "Configured company code settings.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    assert e1.status_code == 201

    # Verify server calculates totals accurately
    detail = api_client.get(f"/api/v1/timesheets/{ts_id}", **auth_headers(employee_user))
    assert detail.status_code == 200
    assert detail.data["total_minutes"] == 480
    assert detail.data["billable_minutes"] == 480

    # AC-02: Submit valid period
    sub = api_client.post(f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user))
    assert sub.status_code == 200
    assert sub.data["status"] == "SUBMITTED"
    assert sub.data["submitted_at"] is not None
    assert sub.data["assigned_approver_id"] == str(approver_user.id)

    # Second submit is rejected with TS_ALREADY_SUBMITTED
    sub2 = api_client.post(f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user))
    assert sub2.status_code == 409
    assert sub2.data["error"]["code"] == "TS_ALREADY_SUBMITTED"

    # Approver sees pending item in queue
    queue = api_client.get("/api/v1/approvals/pending", **auth_headers(approver_user))
    assert queue.status_code == 200
    assert queue.data["meta"]["total"] == 1

    # AC-03: Approver approves
    app = api_client.post(f"/api/v1/timesheets/{ts_id}/approve", {}, format="json", **auth_headers(approver_user))
    assert app.status_code == 200
    assert app.data["status"] == "APPROVED"
    assert app.data["approved_at"] is not None

    # AC-05: Employee cannot edit Approved timesheet
    edit_approved = api_client.patch(
        f"/api/v1/timesheets/{ts_id}/entries/{e1.data['id']}",
        {"duration_minutes": 240},
        format="json",
        **auth_headers(employee_user),
    )
    assert edit_approved.status_code == 409
    assert edit_approved.data["error"]["code"] == "TS_NOT_EDITABLE"


@pytest.mark.django_db
def test_ac04_reject_requires_reason_and_resubmit_and_ac09_reopen(
    api_client,
    employee_user,
    approver_user,
    admin_user,
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

    entry_res = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 120,
            "billable": True,
            "description": "Workshop prep.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    entry_id = entry_res.data["id"]
    api_client.post(f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user))

    # AC-04: Reject without reason fails with APPROVAL_REASON_REQUIRED
    bad_rej = api_client.post(
        f"/api/v1/timesheets/{ts_id}/reject",
        {"reason": "   "},
        format="json",
        **auth_headers(approver_user),
    )
    assert bad_rej.status_code == 400
    assert bad_rej.data["error"]["code"] == "APPROVAL_REASON_REQUIRED"
    assert Timesheet.objects.get(id=ts_id).status == "SUBMITTED"

    # Reject with valid reason returns to employee
    rej = api_client.post(
        f"/api/v1/timesheets/{ts_id}/reject",
        {"reason": "Please add Tuesday hours as well."},
        format="json",
        **auth_headers(approver_user),
    )
    assert rej.status_code == 200
    assert rej.data["status"] == "REJECTED"

    # Employee edits returned entry and resubmits
    upd = api_client.patch(
        f"/api/v1/timesheets/{ts_id}/entries/{entry_id}",
        {"duration_minutes": 240},
        format="json",
        **auth_headers(employee_user),
    )
    assert upd.status_code == 200
    assert api_client.post(
        f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user)
    ).status_code == 200
    assert api_client.post(
        f"/api/v1/timesheets/{ts_id}/approve", {}, format="json", **auth_headers(approver_user)
    ).status_code == 200

    # AC-09: Admin reopens approved timesheet with mandatory reason -> immutable audit + approval event
    reopen_no_reason = api_client.post(
        f"/api/v1/timesheets/{ts_id}/reopen", {}, format="json", **auth_headers(admin_user)
    )
    assert reopen_no_reason.status_code == 400
    assert reopen_no_reason.data["error"]["code"] == "APPROVAL_REASON_REQUIRED"

    reopen = api_client.post(
        f"/api/v1/timesheets/{ts_id}/reopen",
        {"reason": "Client requested WBS reclassification."},
        format="json",
        **auth_headers(admin_user),
    )
    assert reopen.status_code == 200
    assert reopen.data["status"] == "REOPENED"
    assert ApprovalEvent.objects.filter(timesheet_id=ts_id, action="REOPENED").count() == 1
    assert AuditEvent.objects.filter(entity_id=str(ts_id), action="TIMESHEET_REOPENED").count() == 1


@pytest.mark.django_db
def test_ac07_ac08_and_validation_business_rules(
    api_client,
    employee_user,
    active_project,
    closed_project,
    other_project,
    active_task,
    other_project_task,
    active_assignment,
    week_bounds,
):
    period_start, period_end = week_bounds

    # Non-Monday period fails with TS_PERIOD_INVALID
    bad_period = api_client.post(
        "/api/v1/timesheets",
        {"period_start": "2026-11-17", "period_end": "2026-11-23"},
        format="json",
        **auth_headers(employee_user),
    )
    assert bad_period.status_code == 400
    assert bad_period.data["error"]["code"] == "TS_PERIOD_INVALID"

    ts = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end},
        format="json",
        **auth_headers(employee_user),
    )
    assert ts.status_code == 201
    ts_id = ts.data["id"]

    # Duplicate period fails with TS_PERIOD_EXISTS
    dup_period = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end},
        format="json",
        **auth_headers(employee_user),
    )
    assert dup_period.status_code == 409
    assert dup_period.data["error"]["code"] == "TS_PERIOD_EXISTS"

    # Empty submission fails with TS_SUBMISSION_INCOMPLETE
    empty_sub = api_client.post(
        f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user)
    )
    assert empty_sub.status_code == 400
    assert empty_sub.data["error"]["code"] == "TS_SUBMISSION_INCOMPLETE"

    # AC-07: Entry date outside parent period
    outside_date = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": "2026-11-25",
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 60,
            "billable": True,
            "description": "Outside date test.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    assert outside_date.status_code == 400
    assert outside_date.data["error"]["code"] == "TS_ENTRY_DATE_OUTSIDE_PERIOD"

    # AC-08: Duration not multiple of configured increment (15m)
    bad_inc = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 20,
            "billable": True,
            "description": "Invalid increment.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    assert bad_inc.status_code == 400
    assert bad_inc.data["error"]["code"] == "TS_ENTRY_INVALID_DURATION"

    # Task not in project
    wrong_task = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(other_project_task.id),
            "duration_minutes": 60,
            "billable": True,
            "description": "Mismatched task.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    assert wrong_task.status_code == 400
    assert wrong_task.data["error"]["code"] == "TASK_NOT_IN_PROJECT"

    # Unassigned project blocked with ASSIGNMENT_NOT_ACTIVE
    unassigned = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(other_project.id),
            "task_id": str(other_project_task.id),
            "duration_minutes": 60,
            "billable": True,
            "description": "Unassigned work.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    assert unassigned.status_code == 400
    assert unassigned.data["error"]["code"] == "ASSIGNMENT_NOT_ACTIVE"

    # Closed project blocked with PROJECT_INACTIVE
    closed_task = Task.objects.create(project=closed_project, code="LEG-1", name="Legacy Task")
    ProjectAssignment.objects.create(
        user=employee_user, project=closed_project, start_date=date(2025, 1, 1)
    )
    closed_res = api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(closed_project.id),
            "task_id": str(closed_task.id),
            "duration_minutes": 60,
            "billable": False,
            "description": "Closed project attempt.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    assert closed_res.status_code == 400
    assert closed_res.data["error"]["code"] == "PROJECT_INACTIVE"
