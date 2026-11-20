from django.conf import settings
from django.db import models

from common.models import UUIDModel


class Notification(UUIDModel):
    class Type(models.TextChoices):
        TIMESHEET_SUBMITTED = "TIMESHEET_SUBMITTED", "Timesheet Submitted"
        TIMESHEET_APPROVED = "TIMESHEET_APPROVED", "Timesheet Approved"
        TIMESHEET_REJECTED = "TIMESHEET_REJECTED", "Timesheet Rejected"
        TIMESHEET_REOPENED = "TIMESHEET_REOPENED", "Timesheet Reopened"
        DEADLINE_APPROACHING = "DEADLINE_APPROACHING", "Submission Deadline Approaching"
        TIMESHEET_OVERDUE = "TIMESHEET_OVERDUE", "Timesheet Overdue"
        ASSIGNMENT_CHANGED = "ASSIGNMENT_CHANGED", "Assignment Created or Changed"

    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=64, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    read_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(
        max_length=16,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "read_at", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} -> {self.user_id}"
