"""Send deadline-approaching and overdue timesheet reminders."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import emit_notification
from apps.settings_app.services import get_settings
from apps.timesheets.models import Timesheet


class Command(BaseCommand):
    help = "Sends reminders for missing or unsubmitted timesheets for the current period."

    def handle(self, *args, **options):
        settings_dict = get_settings()
        today = timezone.now().date()
        week_start_day = int(settings_dict.get("week_start_day", 0))
        deadline_day = int(settings_dict.get("submission_deadline_day", 4))

        offset = (today.weekday() - week_start_day) % 7
        period_start = today - timedelta(days=offset)
        period_end = period_start + timedelta(days=6)
        deadline_date = period_start + timedelta((deadline_day - week_start_day) % 7)

        is_overdue = today > deadline_date
        notif_type = (
            Notification.Type.TIMESHEET_OVERDUE if is_overdue else Notification.Type.DEADLINE_APPROACHING
        )

        sent_count = 0
        for user in User.objects.filter(status=User.Status.ACTIVE):
            ts = Timesheet.objects.filter(user=user, period_start=period_start).first()
            if ts and ts.status in {Timesheet.Status.SUBMITTED, Timesheet.Status.APPROVED}:
                continue
            already_sent = Notification.objects.filter(
                user=user,
                type=notif_type,
                payload__period_start=str(period_start),
            ).exists()
            if already_sent:
                continue

            emit_notification(
                user=user,
                notification_type=notif_type,
                title=f"Timesheet reminder for {period_start} to {period_end}",
                payload={
                    "period_start": str(period_start),
                    "period_end": str(period_end),
                    "deadline_date": str(deadline_date),
                },
                email_subject=f"Timesheet reminder ({period_start} to {period_end})",
                email_body=(
                    f"Please submit your timesheet for {period_start} to {period_end} "
                    f"(configured deadline: {deadline_date} {settings_dict.get('submission_deadline_time', '17:00')})."
                ),
            )
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Dispatched {sent_count} timesheet reminder(s)."))
