"""Append-only ApprovalEvent model (SRS §6.2, §11)."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.audit.models import AppendOnlyManager
from common.models import UUIDModel


class ApprovalEvent(UUIDModel):
    class Action(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REOPENED = "REOPENED", "Reopened"

    timesheet = models.ForeignKey(
        "timesheets.Timesheet",
        on_delete=models.PROTECT,
        related_name="approval_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_events",
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AppendOnlyManager()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["timesheet", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(action__in=["APPROVED", "REJECTED", "REOPENED"]),
                name="ck_approval_event_action_valid",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("ApprovalEvent records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ApprovalEvent records are strictly append-only and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.action} on {self.timesheet_id} by {self.actor_id}"
