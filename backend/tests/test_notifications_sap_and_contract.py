from pathlib import Path

import pytest
import yaml
from django.core.management import call_command
from drf_spectacular.generators import SchemaGenerator
from openapi_spec_validator import validate

from apps.notifications.models import Notification
from apps.timesheets.models import Timesheet
from integrations.sap.adapter import NullSAPAdapter, build_cats_staging_payload

from .conftest import auth_headers


@pytest.mark.django_db(transaction=True)
def test_notification_email_failure_does_not_rollback_timesheet_submit_or_approve(
    api_client,
    employee_user,
    approver_user,
    active_project,
    active_task,
    active_assignment,
    week_bounds,
    monkeypatch,
):
    period_start, period_end = week_bounds
    ts_res = api_client.post(
        "/api/v1/timesheets",
        {"period_start": period_start, "period_end": period_end},
        format="json",
        **auth_headers(employee_user),
    )
    ts_id = ts_res.data["id"]
    sensitive_desc = "CONFIDENTIAL_WORK_DETAIL_DO_NOT_EMAIL"
    api_client.post(
        f"/api/v1/timesheets/{ts_id}/entries",
        {
            "work_date": period_start,
            "project_id": str(active_project.id),
            "task_id": str(active_task.id),
            "duration_minutes": 120,
            "billable": True,
            "description": sensitive_desc,
        },
        format="json",
        **auth_headers(employee_user),
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("SMTP relay unavailable")

    monkeypatch.setattr("apps.notifications.services.send_mail", _boom)

    sub = api_client.post(
        f"/api/v1/timesheets/{ts_id}/submit", {}, format="json", **auth_headers(employee_user)
    )
    assert sub.status_code == 200
    assert Timesheet.objects.get(id=ts_id).status == "SUBMITTED"
    notif = Notification.objects.get(user=approver_user, type=Notification.Type.TIMESHEET_SUBMITTED)
    assert notif.delivery_status == Notification.DeliveryStatus.FAILED

    # Approve also commits despite email failure
    app = api_client.post(
        f"/api/v1/timesheets/{ts_id}/approve", {}, format="json", **auth_headers(approver_user)
    )
    assert app.status_code == 200
    assert Timesheet.objects.get(id=ts_id).status == "APPROVED"

    # SAP staging adapter accepts approved timesheet
    approved_ts = Timesheet.objects.get(id=ts_id)
    records = build_cats_staging_payload(approved_ts)
    assert len(records) == 1
    assert records[0].hours_decimal == 2.0
    staged = NullSAPAdapter().stage_approved_entries(records, idempotency_key="sap-test-1")
    assert staged["status"] == "STAGED_NOOP"


@pytest.mark.django_db
def test_seed_demo_data_idempotent_and_health_endpoints(api_client):
    call_command("seed_demo_data")
    call_command("seed_demo_data")  # Must be idempotent
    call_command("send_timesheet_reminders")

    login = api_client.post(
        "/api/v1/auth/login",
        {"email": "consultant@sapconsult.example.com", "password": "DemoPass123!"},
        format="json",
    )
    assert login.status_code == 200
    assert "access" in login.data

    live = api_client.get("/api/v1/health/live")
    assert live.status_code == 200
    assert live.data["status"] == "ok"

    ready = api_client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.data["database"] == "ok"


def test_openapi_contract_valid_and_matches_live_django_routes():
    contract_path = Path(__file__).resolve().parent.parent.parent / "timesheet_openapi_django.yaml"
    with contract_path.open("r", encoding="utf-8") as fh:
        contract = yaml.safe_load(fh)

    validate(contract)

    generator = SchemaGenerator()
    live_schema = generator.get_schema(request=None, public=True)
    live_paths = live_schema["paths"]

    for raw_path, ops in contract["paths"].items():
        # drf-spectacular strips SCHEMA_PATH_PREFIX (/api/v1) or preserves depending on config; normalize
        normalized_live = {
            (p[len("/api/v1") :] if p.startswith("/api/v1") else p): methods
            for p, methods in live_paths.items()
        }
        assert raw_path in normalized_live, f"Contract path {raw_path} missing in Django URLs"
        for method in ("get", "post", "patch", "put", "delete"):
            if method in ops:
                assert method in normalized_live[raw_path], (
                    f"Method {method.upper()} {raw_path} missing in live DRF schema"
                )
