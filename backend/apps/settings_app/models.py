"""CompanySetting model for runtime policy configuration (FR-ADM-001)."""

from django.conf import settings
from django.db import models


class CompanySetting(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    value = models.JSONField()
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_settings",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key}={self.value}"
