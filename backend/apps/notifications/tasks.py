from celery import shared_task
from django.core.management import call_command


@shared_task(name="notifications.send_timesheet_reminders")
def send_timesheet_reminders_task() -> str:
    call_command("send_timesheet_reminders")
    return "completed"
