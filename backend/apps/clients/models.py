from django.db import models
from django.db.models import Q

from common.models import TimeStampedModel, UUIDModel


class Client(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["ACTIVE", "INACTIVE"]),
                name="ck_client_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
