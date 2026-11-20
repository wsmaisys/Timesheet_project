from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("full_name", "email")
    list_display = ("employee_code", "full_name", "email", "role", "status", "department", "timezone")
    list_filter = ("role", "status", "department")
    search_fields = ("employee_code", "full_name", "email")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("employee_code", "full_name", "department", "timezone")}),
        (
            "Workforce & RBAC",
            {
                "fields": (
                    "role",
                    "status",
                    "manager",
                    "expected_daily_minutes",
                    "expected_weekly_minutes",
                    "can_override_assignment",
                )
            },
        ),
        ("Django Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "employee_code", "full_name", "role", "password1", "password2"),
            },
        ),
    )
