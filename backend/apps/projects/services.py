"""Domain services for projects, tasks, and row-level project visibility."""

from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F, Q

from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.clients.models import Client
from common.concurrency import check_concurrency
from common.exceptions import DomainError

from .models import Project, Task


def scoped_projects_queryset(user: User):
    base = Project.objects.select_related("client", "project_manager")
    if user.role in {User.Role.ADMIN, User.Role.MANAGEMENT_VIEWER}:
        return base
    if user.role == User.Role.APPROVER:
        return base.filter(
            Q(project_manager=user)
            | Q(assignments__user=user)
            | Q(assignments__user__manager=user)
        ).distinct()
    return base.filter(assignments__user=user).distinct()


def _snapshot_project(project: Project) -> dict[str, Any]:
    return {
        "client_id": str(project.client_id),
        "code": project.code,
        "name": project.name,
        "start_date": str(project.start_date),
        "end_date": str(project.end_date) if project.end_date else None,
        "status": project.status,
        "project_manager_id": str(project.project_manager_id) if project.project_manager_id else None,
        "billable_default": project.billable_default,
        "budget_hours": float(project.budget_hours) if project.budget_hours is not None else None,
        "version": project.version,
    }


def create_project(*, actor: User, payload: dict[str, Any]) -> Project:
    code = payload["code"].strip().upper()
    name = payload["name"].strip()
    if not code or not name:
        raise DomainError("VALIDATION_ERROR", "Project code and name are required.")

    client = Client.objects.filter(id=payload["client_id"]).first()
    if client is None:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Client does not exist.",
            details=[{"field": "client_id", "issue": "not_found"}],
        )
    if client.status != Client.Status.ACTIVE:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Cannot create a project for an inactive client.",
            details=[{"field": "client_id", "issue": "client_inactive"}],
        )

    start_date = payload["start_date"]
    end_date = payload.get("end_date")
    if end_date is not None and end_date < start_date:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Project end_date cannot precede start_date.",
            details=[{"field": "end_date", "issue": "end_before_start"}],
        )

    pm = None
    if pm_id := payload.get("project_manager_id"):
        pm = User.objects.filter(id=pm_id, status=User.Status.ACTIVE).first()
        if pm is None:
            raise DomainError(
                code="VALIDATION_ERROR",
                message="project_manager_id must reference an active user.",
                details=[{"field": "project_manager_id", "issue": "invalid_user"}],
            )

    if Project.objects.filter(code__iexact=code).exists():
        raise DomainError(
            code="PROJECT_CODE_EXISTS",
            message=f"Project with code '{code}' already exists.",
            status_code=409,
        )

    with transaction.atomic():
        try:
            project = Project.objects.create(
                client=client,
                code=code,
                name=name,
                description=(payload.get("description") or None),
                start_date=start_date,
                end_date=end_date,
                status=payload.get("status", Project.Status.ACTIVE),
                project_manager=pm,
                billable_default=bool(payload["billable_default"]),
                budget_hours=payload.get("budget_hours"),
            )
        except IntegrityError:
            raise DomainError(
                code="PROJECT_CODE_EXISTS",
                message=f"Project with code '{code}' already exists.",
                status_code=409,
            )

        record_audit_event(
            actor=actor,
            action="PROJECT_CREATED",
            entity_type="Project",
            entity_id=project.id,
            after_json=_snapshot_project(project),
        )
        return project


def update_project(*, actor: User, request: Any, project: Project, payload: dict[str, Any]) -> Project:
    if actor.role != User.Role.ADMIN:
        raise DomainError("AUTH_FORBIDDEN", "Only administrators can modify projects.", status_code=403)

    with transaction.atomic():
        locked = Project.objects.select_for_update().get(id=project.id)
        check_concurrency(request, "project", locked, payload.get("version"))
        before = _snapshot_project(locked)

        if "name" in payload:
            cleaned = payload["name"].strip()
            if not cleaned:
                raise DomainError("VALIDATION_ERROR", "Project name cannot be empty.")
            locked.name = cleaned
        if "description" in payload:
            desc = payload["description"]
            locked.description = desc.strip() if isinstance(desc, str) and desc.strip() else None
        if "start_date" in payload:
            locked.start_date = payload["start_date"]
        if "end_date" in payload:
            locked.end_date = payload["end_date"]

        if locked.end_date is not None and locked.end_date < locked.start_date:
            raise DomainError(
                code="VALIDATION_ERROR",
                message="Project end_date cannot precede start_date.",
                details=[{"field": "end_date", "issue": "end_before_start"}],
            )

        if "status" in payload:
            locked.status = payload["status"]
        if "project_manager_id" in payload:
            pm_id = payload["project_manager_id"]
            if pm_id is None:
                locked.project_manager = None
            else:
                pm = User.objects.filter(id=pm_id, status=User.Status.ACTIVE).first()
                if pm is None:
                    raise DomainError(
                        code="VALIDATION_ERROR",
                        message="project_manager_id must reference an active user.",
                        details=[{"field": "project_manager_id", "issue": "invalid_user"}],
                    )
                locked.project_manager = pm
        if "billable_default" in payload:
            locked.billable_default = bool(payload["billable_default"])
        if "budget_hours" in payload:
            locked.budget_hours = payload["budget_hours"]

        locked.version = F("version") + 1
        locked.save()
        locked.refresh_from_db()

        record_audit_event(
            actor=actor,
            action="PROJECT_UPDATED",
            entity_type="Project",
            entity_id=locked.id,
            before_json=before,
            after_json=_snapshot_project(locked),
        )
        return locked


def _assert_can_manage_tasks(actor: User, project: Project) -> None:
    if actor.role == User.Role.ADMIN:
        return
    if actor.role == User.Role.APPROVER and project.project_manager_id == actor.id:
        return
    raise DomainError(
        code="AUTH_FORBIDDEN",
        message="Only administrators or the project manager can manage project tasks.",
        status_code=403,
    )


def create_task(*, actor: User, project: Project, payload: dict[str, Any]) -> Task:
    _assert_can_manage_tasks(actor, project)

    if project.status == Project.Status.CLOSED:
        raise DomainError(
            code="PROJECT_INACTIVE",
            message="Cannot add tasks to a closed project.",
            status_code=409,
        )

    code = payload["code"].strip().upper()
    name = payload["name"].strip()
    if not code or not name:
        raise DomainError("VALIDATION_ERROR", "Task code and name are required.")

    if Task.objects.filter(project=project, code__iexact=code).exists():
        raise DomainError(
            code="VALIDATION_ERROR",
            message=f"Task code '{code}' already exists in project '{project.code}'.",
            status_code=409,
            details=[{"field": "code", "issue": "already_exists"}],
        )

    sap_workstream = (payload.get("sap_workstream") or "").strip() or None
    sap_module = (payload.get("sap_module") or "").strip() or None

    with transaction.atomic():
        task = Task.objects.create(
            project=project,
            code=code,
            name=name,
            status=Task.Status.ACTIVE,
            sap_workstream=sap_workstream,
            sap_module=sap_module,
        )
        record_audit_event(
            actor=actor,
            action="TASK_CREATED",
            entity_type="Task",
            entity_id=task.id,
            after_json={
                "project_id": str(project.id),
                "code": task.code,
                "name": task.name,
                "status": task.status,
                "sap_workstream": task.sap_workstream,
                "sap_module": task.sap_module,
            },
        )
        return task


def update_task(*, actor: User, project: Project, task: Task, payload: dict[str, Any]) -> Task:
    _assert_can_manage_tasks(actor, project)
    if task.project_id != project.id:
        raise DomainError(
            code="TASK_NOT_IN_PROJECT",
            message="Task does not belong to the specified project.",
            status_code=400,
        )

    before = {
        "name": task.name,
        "status": task.status,
        "sap_workstream": task.sap_workstream,
        "sap_module": task.sap_module,
    }
    with transaction.atomic():
        if "name" in payload:
            cleaned = payload["name"].strip()
            if not cleaned:
                raise DomainError("VALIDATION_ERROR", "Task name cannot be empty.")
            task.name = cleaned
        if "status" in payload:
            task.status = payload["status"]
        if "sap_workstream" in payload:
            val = payload["sap_workstream"]
            task.sap_workstream = val.strip() if isinstance(val, str) and val.strip() else None
        if "sap_module" in payload:
            val = payload["sap_module"]
            task.sap_module = val.strip() if isinstance(val, str) and val.strip() else None
        task.save()
        record_audit_event(
            actor=actor,
            action="TASK_UPDATED",
            entity_type="Task",
            entity_id=task.id,
            before_json=before,
            after_json={
                "name": task.name,
                "status": task.status,
                "sap_workstream": task.sap_workstream,
                "sap_module": task.sap_module,
            },
        )
        return task
