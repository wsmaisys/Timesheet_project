"""Idempotent demo seed data for immediate stakeholder walkthrough and UAT."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.services import approve_timesheet, reject_timesheet
from apps.assignments.models import ProjectAssignment
from apps.clients.models import Client
from apps.projects.models import Project, Task
from apps.settings_app.services import get_settings, update_settings
from apps.timesheets.models import Timesheet
from apps.timesheets.services import add_time_entry, create_timesheet, submit_timesheet


class _DummyRequest:
    headers: dict[str, str] = {}


def _ensure_demo_user(email: str, defaults: dict) -> User:
    user, created = User.objects.get_or_create(email=email, defaults=defaults)
    if created or not user.password or not user.has_usable_password():
        user.set_password("DemoPass123!")
        user.save(update_fields=["password"])
    return user


class Command(BaseCommand):
    help = "Seeds realistic SAP consulting demo users, clients, projects, tasks, assignments, and timesheets."

    def handle(self, *args, **options):
        today = timezone.now().date()
        current_monday = today - timedelta(days=today.weekday())
        last_monday = current_monday - timedelta(days=7)
        two_weeks_ago = current_monday - timedelta(days=14)

        # Users
        admin = _ensure_demo_user(
            "admin@sapconsult.example.com",
            {
                "employee_code": "EMP-001",
                "full_name": "Ananya Deshmukh",
                "role": User.Role.ADMIN,
                "status": User.Status.ACTIVE,
                "department": "Operations",
                "timezone": "Asia/Kolkata",
                "is_staff": True,
            },
        )

        # Ensure baseline settings exist
        if not get_settings():
            update_settings(actor=admin, updates={"entry_increment_minutes": 15})

        manager = _ensure_demo_user(
            "manager@sapconsult.example.com",
            {
                "employee_code": "EMP-002",
                "full_name": "Rohan Kulkarni",
                "role": User.Role.APPROVER,
                "status": User.Status.ACTIVE,
                "department": "SAP Delivery",
                "timezone": "Asia/Kolkata",
            },
        )

        consultant = _ensure_demo_user(
            "consultant@sapconsult.example.com",
            {
                "employee_code": "EMP-003",
                "full_name": "Meera Nair",
                "role": User.Role.EMPLOYEE,
                "status": User.Status.ACTIVE,
                "manager": manager,
                "department": "SAP Delivery",
                "timezone": "Asia/Kolkata",
            },
        )

        consultant2 = _ensure_demo_user(
            "abap.dev@sapconsult.example.com",
            {
                "employee_code": "EMP-004",
                "full_name": "Vikram Sethi",
                "role": User.Role.EMPLOYEE,
                "status": User.Status.ACTIVE,
                "manager": manager,
                "department": "SAP Technology",
                "timezone": "Europe/Berlin",
            },
        )

        _ensure_demo_user(
            "director@sapconsult.example.com",
            {
                "employee_code": "EMP-005",
                "full_name": "Priya Menon",
                "role": User.Role.MANAGEMENT_VIEWER,
                "status": User.Status.ACTIVE,
                "department": "SAP Delivery",
                "timezone": "Asia/Kolkata",
            },
        )

        # Clients
        c_acme, _ = Client.objects.get_or_create(
            code="ACME-IND",
            defaults={"name": "Acme Industrials Ltd", "status": Client.Status.ACTIVE},
        )
        c_nord, _ = Client.objects.get_or_create(
            code="NORD-LOG",
            defaults={"name": "Nordic Logistics AG", "status": Client.Status.ACTIVE},
        )
        c_int, _ = Client.objects.get_or_create(
            code="INTERNAL",
            defaults={"name": "Internal Practice & Bench", "status": Client.Status.ACTIVE},
        )

        # Projects
        p_s4, _ = Project.objects.get_or_create(
            code="PRJ-S4-FIN",
            defaults={
                "client": c_acme,
                "name": "S/4HANA Finance Greenfield",
                "description": "Core FI/CO greenfield rollout across 3 company codes.",
                "start_date": two_weeks_ago - timedelta(days=30),
                "end_date": current_monday + timedelta(days=120),
                "status": Project.Status.ACTIVE,
                "project_manager": manager,
                "billable_default": True,
                "budget_hours": 1200,
            },
        )
        p_btp, _ = Project.objects.get_or_create(
            code="PRJ-BTP-INT",
            defaults={
                "client": c_nord,
                "name": "SAP BTP Integration Suite",
                "description": "EDI and warehouse API integration on SAP BTP.",
                "start_date": two_weeks_ago - timedelta(days=20),
                "end_date": current_monday + timedelta(days=90),
                "status": Project.Status.ACTIVE,
                "project_manager": manager,
                "billable_default": True,
                "budget_hours": 600,
            },
        )
        p_int, _ = Project.objects.get_or_create(
            code="INT-ENABLE",
            defaults={
                "client": c_int,
                "name": "Internal Practice & Enablement",
                "description": "Internal certifications, townhalls, and pre-sales support.",
                "start_date": two_weeks_ago - timedelta(days=60),
                "end_date": None,
                "status": Project.Status.ACTIVE,
                "project_manager": admin,
                "billable_default": False,
                "budget_hours": None,
            },
        )

        # Tasks
        t_fico, _ = Task.objects.get_or_create(
            project=p_s4,
            code="FI-GL-CFG",
            defaults={
                "name": "General Ledger & Chart of Accounts Config",
                "sap_module": "FI",
                "sap_workstream": "Build & Config",
            },
        )
        t_co, _ = Task.objects.get_or_create(
            project=p_s4,
            code="CO-PC-MIG",
            defaults={
                "name": "Profit Center Master Data Migration",
                "sap_module": "CO",
                "sap_workstream": "Data Migration",
            },
        )
        t_btp, _ = Task.objects.get_or_create(
            project=p_btp,
            code="BTP-CPI-01",
            defaults={
                "name": "CPI iFlow Development & Error Handling",
                "sap_module": "BTP",
                "sap_workstream": "Build & Config",
            },
        )
        t_int, _ = Task.objects.get_or_create(
            project=p_int,
            code="INT-TRN",
            defaults={
                "name": "SAP Certification & Practice Sync",
                "sap_module": "S/4HANA Migration",
                "sap_workstream": "Internal",
            },
        )

        # Assignments
        for u in (consultant, manager, consultant2):
            for proj in (p_s4, p_int):
                ProjectAssignment.objects.get_or_create(
                    user=u,
                    project=proj,
                    start_date=two_weeks_ago - timedelta(days=30),
                    defaults={"end_date": None, "allocation_percent": 50},
                )
        ProjectAssignment.objects.get_or_create(
            user=consultant2,
            project=p_btp,
            start_date=two_weeks_ago - timedelta(days=30),
            defaults={"end_date": None, "allocation_percent": 50},
        )

        dummy_req = _DummyRequest()

        # Sample Approved week (2 weeks ago) for consultant
        if not Timesheet.objects.filter(user=consultant, period_start=two_weeks_ago).exists():
            ts_old = create_timesheet(
                actor=consultant,
                period_start=two_weeks_ago,
                period_end=two_weeks_ago + timedelta(days=6),
                notes="Baseline FI/CO configuration week.",
            )
            for i in range(5):
                add_time_entry(
                    actor=consultant,
                    timesheet=ts_old,
                    payload={
                        "work_date": two_weeks_ago + timedelta(days=i),
                        "project_id": p_s4.id,
                        "task_id": t_fico.id if i < 3 else t_co.id,
                        "duration_minutes": 480,
                        "billable": True,
                        "description": f"Configured ledger rules and validated posting keys (Day {i + 1}).",
                    },
                )
            ts_old = submit_timesheet(actor=consultant, request=dummy_req, timesheet=ts_old)
            approve_timesheet(actor=manager, request=dummy_req, timesheet=ts_old)

        # Sample Submitted week (last week) for consultant2 waiting in manager's approval queue
        if not Timesheet.objects.filter(user=consultant2, period_start=last_monday).exists():
            ts_sub = create_timesheet(
                actor=consultant2,
                period_start=last_monday,
                period_end=last_monday + timedelta(days=6),
                notes="Completed CPI iFlow integration tests.",
            )
            for i in range(4):
                add_time_entry(
                    actor=consultant2,
                    timesheet=ts_sub,
                    payload={
                        "work_date": last_monday + timedelta(days=i),
                        "project_id": p_btp.id,
                        "task_id": t_btp.id,
                        "duration_minutes": 450,
                        "billable": True,
                        "description": f"Implemented BTP CPI mapping and unit tested ASN flow ({i + 1}).",
                    },
                )
            add_time_entry(
                actor=consultant2,
                timesheet=ts_sub,
                payload={
                    "work_date": last_monday + timedelta(days=4),
                    "project_id": p_int.id,
                    "task_id": t_int.id,
                    "duration_minutes": 240,
                    "billable": False,
                    "description": "SAP BTP Security workshop and architecture review.",
                },
            )
            submit_timesheet(actor=consultant2, request=dummy_req, timesheet=ts_sub)

        # Sample Rejected week (last week) for consultant so rejection banner & edit flow is visible
        if not Timesheet.objects.filter(user=consultant, period_start=last_monday).exists():
            ts_rej = create_timesheet(
                actor=consultant,
                period_start=last_monday,
                period_end=last_monday + timedelta(days=6),
            )
            add_time_entry(
                actor=consultant,
                timesheet=ts_rej,
                payload={
                    "work_date": last_monday,
                    "project_id": p_s4.id,
                    "task_id": t_fico.id,
                    "duration_minutes": 480,
                    "billable": True,
                    "description": "GL workshops with client finance lead.",
                },
            )
            ts_rej = submit_timesheet(actor=consultant, request=dummy_req, timesheet=ts_rej)
            reject_timesheet(
                actor=manager,
                request=dummy_req,
                timesheet=ts_rej,
                reason="Missing Tuesday to Friday entries for S/4HANA Finance sprint. Please complete and resubmit.",
            )

        # Sample Draft week (current week) for consultant
        if not Timesheet.objects.filter(user=consultant, period_start=current_monday).exists():
            ts_cur = create_timesheet(
                actor=consultant,
                period_start=current_monday,
                period_end=current_monday + timedelta(days=6),
                notes="Current week draft.",
            )
            add_time_entry(
                actor=consultant,
                timesheet=ts_cur,
                payload={
                    "work_date": current_monday,
                    "project_id": p_s4.id,
                    "task_id": t_co.id,
                    "duration_minutes": 360,
                    "billable": True,
                    "description": "Loaded profit center hierarchy into QAS and verified cost center mapping.",
                },
            )
            add_time_entry(
                actor=consultant,
                timesheet=ts_cur,
                payload={
                    "work_date": current_monday,
                    "project_id": p_int.id,
                    "task_id": t_int.id,
                    "duration_minutes": 120,
                    "billable": False,
                    "description": "Weekly SAP practice knowledge sharing session.",
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo users (password: DemoPass123!), clients, projects, tasks, assignments, and timesheets."
            )
        )
