"""Shared abstract base models for all domain apps."""

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract base providing an opaque UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract base recording UTC creation and update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
