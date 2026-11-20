"""Project and Task models with SAP workstream/module classification (SRS §11 & §16)."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models import TimeStampedModel, UUIDModel


class Project(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ON_HOLD = "ON_HOLD", "On Hold"
        CLOSED = "CLOSED", "Closed"

    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="projects")
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="managed_projects",
    )
    billable_default = models.BooleanField(default=True)
    budget_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="ck_project_dates_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "ACTIVE", "ON_HOLD", "CLOSED"]),
                name="ck_project_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(budget_hours__isnull=True) | Q(budget_hours__gte=0),
                name="ck_project_budget_nonneg",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Task(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="tasks")
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    sap_workstream = models.CharField(max_length=64, null=True, blank=True)
    sap_module = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["project", "code"], name="uq_task_project_code"),
            models.CheckConstraint(
                condition=Q(status__in=["ACTIVE", "INACTIVE"]),
                name="ck_task_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.code}/{self.code} - {self.name}"
