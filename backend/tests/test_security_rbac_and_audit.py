import os
import subprocess
import sys
from datetime import date

import pytest

from apps.accounts.models import User
from apps.approvals.models import ApprovalEvent
from apps.assignments.models import ProjectAssignment
from apps.audit.models import AuditEvent
from apps.timesheets.models import TimeEntry, Timesheet

from .conftest import auth_headers


@pytest.mark.django_db
def test_unauthenticated_and_inactive_user_blocked(api_client, employee_user):
    unauth = api_client.get("/api/v1/timesheets")
    assert unauth.status_code == 401
    assert unauth.data["error"]["code"] == "AUTH_INVALID_TOKEN"
    assert "request_id" in unauth.data["error"]

    # Issue valid JWT, then deactivate user
    headers = auth_headers(employee_user)
    employee_user.status = User.Status.INACTIVE
    employee_user.save()

    blocked_token = api_client.get("/api/v1/auth/me", **headers)
    assert blocked_token.status_code == 403
    assert blocked_token.data["error"]["code"] == "AUTH_ACCOUNT_DISABLED"

    blocked_login = api_client.post(
        "/api/v1/auth/login",
        {"email": employee_user.email, "password": "Password123!"},
        format="json",
    )
    assert blocked_login.status_code == 403
    assert blocked_login.data["error"]["code"] == "AUTH_ACCOUNT_DISABLED"


@pytest.mark.django_db
def test_ac06_idor_and_self_role_escalation_and_self_approval_blocked(
    api_client,
    employee_user,
    other_employee_user,
    approver_user,
    other_approver_user,
    active_project,
    active_task,
    active_assignment,
    week_bounds,
):
    period_start, period_end = week_bounds

    # Employee cannot escalate own role or status
    esc = api_client.patch(
        f"/api/v1/users/{employee_user.id}",
        {"role": "ADMIN"},
        format="json",
        **auth_headers(employee_user),
    )
    assert esc.status_code == 403
    assert esc.data["error"]["code"] == "AUTH_FORBIDDEN"

    # Employee creates & submits timesheet
    ts = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end},
        format="json",
        **auth_headers(employee_user),
    )
    ts_id = ts.data["id"]
    api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 120,
            "billable": True,
            "description": "Design review.",
        },
        format="json",
        **auth_headers(employee_user),
    )
    api_client.post(f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user))

    # AC-06: Other employee cannot read employee's timesheet
    idor = api_client.get(f"/api/v1/timesheets/{ts_id}", **auth_headers(other_employee_user))
    assert idor.status_code == 403
    assert idor.data["error"]["code"] == "AUTH_FORBIDDEN"

    # Out-of-scope approver cannot approve
    out_of_scope = api_client.post(
        f"/api/v1/timesheets/{ts_id}/approve", {}, format="json", **auth_headers(other_approver_user)
    )
    assert out_of_scope.status_code == 403
    assert out_of_scope.data["error"]["code"] == "APPROVER_OUT_OF_SCOPE"

    # Approver cannot self-approve own timesheet
    ProjectAssignment.objects.create(
        user=approver_user,
        project=active_project,
        start_date=date(2026, 1, 1),
    )
    mgr_ts = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end},
        format="json",
        **auth_headers(approver_user),
    )
    mgr_ts_id = mgr_ts.data["id"]
    api_client.post(
        f"/api/v1/timesheets/{mgr_ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 60,
            "billable": True,
            "description": "Manager work.",
        },
        format="json",
        **auth_headers(approver_user),
    )
    api_client.post(f"/api/v1/timesheets/{mgr_ts_id}/submit", {}, format="json", **auth_headers(approver_user))
    self_app = api_client.post(
        f"/api/v1/timesheets/{mgr_ts_id}/approve", {}, format="json", **auth_headers(approver_user)
    )
    assert self_app.status_code == 403
    assert self_app.data["error"]["code"] == "APPROVER_OUT_OF_SCOPE"


@pytest.mark.django_db
def test_ac10_department_report_and_csv_isolation_and_formula_escape(
    api_client,
    employee_user,
    other_employee_user,
    dept_viewer_user,
    active_project,
    other_project,
    active_task,
    other_project_task,
    active_assignment,
    week_bounds,
):
    period_start, period_end = week_bounds

    # Employee in "SAP Delivery"
    ts1 = Timesheet.objects.create(
        user=employee_user,
        period_start=date.fromisoformat(period_start),
        period_end=date.fromisoformat(period_end),
        status=Timesheet.Status.APPROVED,
    )
    TimeEntry.objects.create(
        timesheet=ts1,
        project=active_project,
        task=active_task,
        work_date=date.fromisoformat(period_start),
        duration_minutes=240,
        billable=True,
        description="Delivery task",
    )

    # Other employee in "SAP Technology" with formula-looking name
    other_employee_user.full_name = "=CMD('calc')"
    other_employee_user.save()
    ts2 = Timesheet.objects.create(
        user=other_employee_user,
        period_start=date.fromisoformat(period_start),
        period_end=date.fromisoformat(period_end),
        status=Timesheet.Status.APPROVED,
    )
    TimeEntry.objects.create(
        timesheet=ts2,
        project=other_project,
        task=other_project_task,
        work_date=date.fromisoformat(period_start),
        duration_minutes=180,
        billable=True,
        description="Tech task",
    )

    # AC-10: Management Viewer scoped to "SAP Delivery" never sees "SAP Technology" rows
    rpt = api_client.get(
        f"/api/v1/reports/time-summary?from_date={period_start}&to_date={period_end}",
        **auth_headers(dept_viewer_user),
    )
    assert rpt.status_code == 200
    assert len(rpt.data) == 1
    assert rpt.data[0]["user_id"] == str(employee_user.id)

    csv_res = api_client.get(
        f"/api/v1/reports/time-summary/export?from_date={period_start}&to_date={period_end}",
        **auth_headers(dept_viewer_user),
    )
    assert csv_res.status_code == 200
    assert csv_res["Content-Type"].startswith("text/csv")
    body = csv_res.content.decode("utf-8")
    assert employee_user.employee_code in body
    assert other_employee_user.employee_code not in body

    # Formula injection neutralization check when other_employee exports own data
    csv_self = api_client.get(
        f"/api/v1/reports/time-summary/export?from_date={period_start}&to_date={period_end}",
        **auth_headers(other_employee_user),
    )
    assert "'=CMD('calc')" in csv_self.content.decode("utf-8")


@pytest.mark.django_db
def test_audit_and_approval_events_append_only_and_restricted(
    api_client,
    admin_user,
    employee_user,
    approver_user,
    week_bounds,
):
    # Non-admin cannot query audit events
    forbidden = api_client.get("/api/v1/audit-events", **auth_headers(employee_user))
    assert forbidden.status_code == 403
    assert forbidden.data["error"]["code"] == "AUTH_FORBIDDEN"

    evt = AuditEvent.objects.create(
        actor=admin_user,
        actor_email=admin_user.email,
        action="TEST_EVT",
        entity_type="Test",
        entity_id="1",
        request_id="req_test",
    )
    with pytest.raises(ValueError):
        evt.action = "TAMPERED"
        evt.save()
    with pytest.raises(ValueError):
        evt.delete()
    with pytest.raises(ValueError):
        AuditEvent.objects.filter(id=evt.id).delete()

    period_start, period_end = week_bounds
    ts = Timesheet.objects.create(
        user=employee_user,
        period_start=date.fromisoformat(period_start),
        period_end=date.fromisoformat(period_end),
        status=Timesheet.Status.APPROVED,
    )
    app_evt = ApprovalEvent.objects.create(
        timesheet=ts,
        actor=approver_user,
        action=ApprovalEvent.Action.APPROVED,
    )
    with pytest.raises(ValueError):
        app_evt.reason = "Tampered"
        app_evt.save()
    with pytest.raises(ValueError):
        app_evt.delete()


@pytest.mark.django_db
def test_invalid_uuid_query_param_returns_400_error_envelope(api_client, employee_user):
    res = api_client.get(
        "/api/v1/timesheets?project_id=not-a-uuid",
        **auth_headers(employee_user),
    )
    assert res.status_code == 400
    assert res.data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in res.data["error"]


def test_prod_settings_fail_fast_without_secret_key():
    from pathlib import Path

    env = os.environ.copy()
    env.pop("DJANGO_SECRET_KEY", None)
    env.pop("DATABASE_URL", None)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
    proc = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        env=env,
        cwd=str(Path(__file__).resolve().parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "ImproperlyConfigured" in proc.stderr
