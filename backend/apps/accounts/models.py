"""Custom User model with RBAC roles, manager hierarchy, and timezone."""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from common.models import TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        normalized_email = self.normalize_email(email).strip().lower()
        employee_code = (extra_fields.pop("employee_code", "") or "").strip()
        if not employee_code:
            raise ValueError("Users must have an employee_code.")

        status = extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields["is_active"] = status == User.Status.ACTIVE
        user = self.model(email=normalized_email, employee_code=employee_code, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("timezone", "UTC")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, UUIDModel, TimeStampedModel):
    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        APPROVER = "APPROVER", "Manager / Approver"
        ADMIN = "ADMIN", "Administrator"
        MANAGEMENT_VIEWER = "MANAGEMENT_VIEWER", "Management Viewer"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    employee_code = models.CharField(max_length=64, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.EMPLOYEE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    manager = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    department = models.CharField(max_length=128, null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    expected_daily_minutes = models.PositiveIntegerField(null=True, blank=True)
    expected_weekly_minutes = models.PositiveIntegerField(null=True, blank=True)
    can_override_assignment = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["employee_code", "full_name"]

    class Meta:
        ordering = ["full_name", "email"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="uq_user_lower_email"),
            models.CheckConstraint(
                condition=Q(role__in=["EMPLOYEE", "APPROVER", "ADMIN", "MANAGEMENT_VIEWER"]),
                name="ck_user_role_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["ACTIVE", "INACTIVE"]),
                name="ck_user_status_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        self.employee_code = (self.employee_code or "").strip()
        self.full_name = (self.full_name or "").strip()
        self.is_active = self.status == self.Status.ACTIVE
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.employee_code})"
