"""Server-side RBAC permission classes (deny-by-default)."""

from rest_framework.permissions import BasePermission


class IsActiveUser(BasePermission):
    """Ensures caller is authenticated and has ACTIVE account status."""

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_active", False)
            and getattr(user, "status", None) == "ACTIVE"
        )


class IsAdmin(IsActiveUser):
    """Restricts access strictly to ADMIN users."""

    def has_permission(self, request, view) -> bool:
        return super().has_permission(request, view) and request.user.role == "ADMIN"


class IsApproverOrAdmin(IsActiveUser):
    """Restricts access to APPROVER and ADMIN roles."""

    def has_permission(self, request, view) -> bool:
        return super().has_permission(request, view) and request.user.role in {"APPROVER", "ADMIN"}


class CanViewReports(IsActiveUser):
    """Allows roles permitted to query scoped time reports."""

    def has_permission(self, request, view) -> bool:
        return super().has_permission(request, view) and request.user.role in {
            "ADMIN",
            "APPROVER",
            "MANAGEMENT_VIEWER",
            "EMPLOYEE",
        }


class CanViewAudit(IsAdmin):
    """Audit logs are restricted strictly to ADMIN users."""
