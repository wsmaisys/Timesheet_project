from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models import TimeStampedModel, UUIDModel


class ProjectAssignment(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    allocation_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "project__code"]
        indexes = [
            models.Index(fields=["user", "project", "start_date", "end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="ck_assignment_dates_valid",
            ),
            models.CheckConstraint(
                condition=Q(allocation_percent__isnull=True)
                | (Q(allocation_percent__gte=0) & Q(allocation_percent__lte=100)),
                name="ck_assignment_alloc_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.employee_code} -> {self.project.code} ({self.start_date}..{self.end_date or 'open'})"
