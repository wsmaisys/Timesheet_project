"""Effective permission strings exposed via /auth/me and /auth/login."""

from .models import User

ROLE_PERMISSIONS: dict[str, list[str]] = {
    User.Role.EMPLOYEE: [
        "timesheet:read_own",
        "timesheet:write_own",
        "timesheet:submit_own",
        "project:read_assigned",
        "report:read_own",
        "report:export_own",
    ],
    User.Role.APPROVER: [
        "timesheet:read_own",
        "timesheet:write_own",
        "timesheet:submit_own",
        "timesheet:read_team",
        "timesheet:approve_team",
        "timesheet:reject_team",
        "timesheet:reopen_team",
        "project:read_scoped",
        "task:manage_pm",
        "assignment:manage_pm",
        "report:read_team",
        "report:export_team",
    ],
    User.Role.ADMIN: [
        "timesheet:read_all",
        "timesheet:write_own",
        "timesheet:submit_own",
        "timesheet:approve_all",
        "timesheet:reject_all",
        "timesheet:reopen_all",
        "user:manage",
        "client:manage",
        "project:manage",
        "task:manage",
        "assignment:manage",
        "settings:manage",
        "report:read_all",
        "report:export_all",
        "audit:read",
    ],
    User.Role.MANAGEMENT_VIEWER: [
        "timesheet:read_own",
        "timesheet:write_own",
        "timesheet:submit_own",
        "project:read_all",
        "report:read_scoped",
        "report:export_scoped",
    ],
}


def get_effective_permissions(user: User) -> list[str]:
    return list(ROLE_PERMISSIONS.get(user.role, []))
