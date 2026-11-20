"""Append-only AuditEvent model (FR-AUD-001, AC-09)."""

import uuid

from django.conf import settings
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def delete(self):
        raise ValueError("AuditEvent records are strictly append-only and cannot be deleted.")

    def update(self, **kwargs):
        raise ValueError("AuditEvent records are strictly append-only and cannot be modified.")


class AppendOnlyManager(models.Manager):
    def get_queryset(self):
        return AppendOnlyQuerySet(self.model, using=self._db)


class AuditEvent(models.Model):
    """Immutable audit trail entry for material changes and workflow transitions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_email = models.EmailField(max_length=254)
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=128, db_index=True)
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)
    request_id = models.CharField(max_length=128, default="-", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id} by {self.actor_email}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditEvent records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEvent records are strictly append-only and cannot be deleted.")
