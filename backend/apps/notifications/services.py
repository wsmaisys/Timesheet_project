"""Fault-isolated notification outbox service (SRS §15)."""

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)


def _deliver_email_safe(notification_id: Any, subject: str | None, body: str | None) -> None:
    """Attempts email delivery without ever raising or rolling back domain mutations."""
    notification = Notification.objects.select_related("user").filter(id=notification_id).first()
    if notification is None:
        return

    if not subject or not body or not notification.user.email:
        Notification.objects.filter(id=notification_id).update(delivery_status=Notification.DeliveryStatus.SENT)
        return

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            fail_silently=False,
        )
        Notification.objects.filter(id=notification_id).update(delivery_status=Notification.DeliveryStatus.SENT)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Email notification delivery failed for notification=%s: %s",
            notification_id,
            exc,
        )
        Notification.objects.filter(id=notification_id).update(
            delivery_status=Notification.DeliveryStatus.FAILED
        )


def emit_notification(
    *,
    user: Any,
    notification_type: str,
    title: str,
    payload: dict[str, Any],
    email_subject: str | None = None,
    email_body: str | None = None,
) -> Notification | None:
    """Persists an in-app notification and schedules fault-isolated email dispatch."""
    if user is None:
        return None

    notification = Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        payload=payload,
        delivery_status=Notification.DeliveryStatus.PENDING,
    )
    transaction.on_commit(
        lambda nid=notification.id, subj=email_subject, msg=email_body: _deliver_email_safe(nid, subj, msg)
    )
    return notification


def mark_read(*, user: Any, notification_id: Any) -> Notification | None:
    notification = Notification.objects.filter(id=notification_id, user=user).first()
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return notification


def mark_all_read(*, user: Any) -> int:
    return Notification.objects.filter(user=user, read_at__isnull=True).update(read_at=timezone.now())
