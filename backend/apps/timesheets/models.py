"""Timesheet, TimeEntry, and IdempotencyRecord models (SRS §11)."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models import TimeStampedModel, UUIDModel


class Timesheet(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        REJECTED = "REJECTED", "Rejected"
        APPROVED = "APPROVED", "Approved"
        REOPENED = "REOPENED", "Reopened"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="timesheets",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(null=True, blank=True)
    assigned_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_approval_timesheets",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-period_start", "user__full_name"]
        indexes = [
            models.Index(fields=["user", "period_start", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "period_start"], name="uq_timesheet_user_period_start"),
            models.CheckConstraint(
                condition=Q(period_end__gte=F("period_start")),
                name="ck_timesheet_period_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "SUBMITTED", "REJECTED", "APPROVED", "REOPENED", "CANCELLED"]),
                name="ck_timesheet_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.employee_code} [{self.period_start}..{self.period_end}] ({self.status})"


class TimeEntry(UUIDModel, TimeStampedModel):
    timesheet = models.ForeignKey(Timesheet, on_delete=models.PROTECT, related_name="entries")
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="time_entries")
    task = models.ForeignKey("projects.Task", on_delete=models.PROTECT, related_name="time_entries")
    work_date = models.DateField()
    duration_minutes = models.PositiveIntegerField()
    billable = models.BooleanField(default=True)
    description = models.TextField()

    class Meta:
        ordering = ["work_date", "created_at"]
        indexes = [
            models.Index(fields=["project", "work_date"]),
            models.Index(fields=["timesheet", "work_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(duration_minutes__gt=0),
                name="ck_time_entry_positive_duration",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.work_date} {self.project.code}/{self.task.code} ({self.duration_minutes}m)"


class IdempotencyRecord(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    key = models.CharField(max_length=128)
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key", "method", "path"],
                name="uq_idempotency_scope",
            ),
        ]
