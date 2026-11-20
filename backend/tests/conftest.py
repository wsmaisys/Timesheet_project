from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.assignments.models import ProjectAssignment
from apps.clients.models import Client
from apps.projects.models import Project, Task


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def auth_headers(user: User, **extra) -> dict[str, str]:
    token = str(RefreshToken.for_user(user).access_token)
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    headers.update(extra)
    return headers


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_user(
        email="admin@test.local",
        password="Password123!",
        employee_code="T-ADM-01",
        full_name="Admin One",
        role=User.Role.ADMIN,
        department="Operations",
        timezone="UTC",
    )


@pytest.fixture
def approver_user(db) -> User:
    return User.objects.create_user(
        email="manager@test.local",
        password="Password123!",
        employee_code="T-MGR-01",
        full_name="Manager One",
        role=User.Role.APPROVER,
        department="SAP Delivery",
        timezone="Asia/Kolkata",
    )


@pytest.fixture
def other_approver_user(db) -> User:
    return User.objects.create_user(
        email="other.mgr@test.local",
        password="Password123!",
        employee_code="T-MGR-02",
        full_name="Other Manager",
        role=User.Role.APPROVER,
        department="SAP Technology",
        timezone="UTC",
    )


@pytest.fixture
def employee_user(db, approver_user: User) -> User:
    return User.objects.create_user(
        email="emp@test.local",
        password="Password123!",
        employee_code="T-EMP-01",
        full_name="Employee One",
        role=User.Role.EMPLOYEE,
        manager=approver_user,
        department="SAP Delivery",
        timezone="Asia/Kolkata",
    )


@pytest.fixture
def other_employee_user(db, other_approver_user: User) -> User:
    return User.objects.create_user(
        email="other.emp@test.local",
        password="Password123!",
        employee_code="T-EMP-02",
        full_name="Employee Two",
        role=User.Role.EMPLOYEE,
        manager=other_approver_user,
        department="SAP Technology",
        timezone="UTC",
    )


@pytest.fixture
def dept_viewer_user(db) -> User:
    return User.objects.create_user(
        email="viewer@test.local",
        password="Password123!",
        employee_code="T-VW-01",
        full_name="Delivery Viewer",
        role=User.Role.MANAGEMENT_VIEWER,
        department="SAP Delivery",
        timezone="UTC",
    )


@pytest.fixture
def client_obj(db) -> Client:
    return Client.objects.create(code="CL-001", name="Acme Corp", status=Client.Status.ACTIVE)


@pytest.fixture
def active_project(db, client_obj: Client, approver_user: User) -> Project:
    return Project.objects.create(
        client=client_obj,
        code="PRJ-FI-01",
        name="S/4HANA FI Rollout",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=Project.Status.ACTIVE,
        project_manager=approver_user,
        billable_default=True,
        budget_hours=1000,
    )


@pytest.fixture
def closed_project(db, client_obj: Client, approver_user: User) -> Project:
    return Project.objects.create(
        client=client_obj,
        code="PRJ-OLD-01",
        name="Legacy ECC Support",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        status=Project.Status.CLOSED,
        project_manager=approver_user,
        billable_default=False,
    )


@pytest.fixture
def other_project(db, client_obj: Client, other_approver_user: User) -> Project:
    return Project.objects.create(
        client=client_obj,
        code="PRJ-BTP-02",
        name="BTP Extension Suite",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=Project.Status.ACTIVE,
        project_manager=other_approver_user,
        billable_default=True,
    )


@pytest.fixture
def active_task(db, active_project: Project) -> Task:
    return Task.objects.create(
        project=active_project,
        code="FI-CFG",
        name="Ledger Configuration",
        status=Task.Status.ACTIVE,
        sap_module="FI",
        sap_workstream="Build & Config",
    )


@pytest.fixture
def other_project_task(db, other_project: Project) -> Task:
    return Task.objects.create(
        project=other_project,
        code="BTP-DEV",
        name="CAP Service Dev",
        status=Task.Status.ACTIVE,
        sap_module="BTP",
        sap_workstream="Build & Config",
    )


@pytest.fixture
def active_assignment(db, employee_user: User, active_project: Project) -> ProjectAssignment:
    return ProjectAssignment.objects.create(
        user=employee_user,
        project=active_project,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        allocation_percent=100,
    )


@pytest.fixture
def week_bounds() -> tuple[str, str]:
    start = date(2026, 11, 16)  # Monday
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()
