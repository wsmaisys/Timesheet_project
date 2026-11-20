from django.urls import path

from .views import (
    ApproveTimesheetView,
    PendingApprovalsListView,
    RejectTimesheetView,
    ReopenTimesheetView,
)

urlpatterns = [
    path("approvals/pending", PendingApprovalsListView.as_view(), name="approvals-pending"),
    path("timesheets/<uuid:timesheet_id>/approve", ApproveTimesheetView.as_view(), name="timesheet-approve"),
    path("timesheets/<uuid:timesheet_id>/reject", RejectTimesheetView.as_view(), name="timesheet-reject"),
    path("timesheets/<uuid:timesheet_id>/reopen", ReopenTimesheetView.as_view(), name="timesheet-reopen"),
]
