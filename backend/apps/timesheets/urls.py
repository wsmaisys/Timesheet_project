from django.urls import path

from .views import (
    TimeEntryCreateView,
    TimeEntryDetailView,
    TimesheetDetailView,
    TimesheetListCreateView,
    TimesheetSubmitView,
)

urlpatterns = [
    path("timesheets", TimesheetListCreateView.as_view(), name="timesheet-list-create"),
    path("timesheets/<uuid:timesheet_id>", TimesheetDetailView.as_view(), name="timesheet-detail"),
    path("timesheets/<uuid:timesheet_id>/entries", TimeEntryCreateView.as_view(), name="time-entry-create"),
    path(
        "timesheets/<uuid:timesheet_id>/entries/<uuid:entry_id>",
        TimeEntryDetailView.as_view(),
        name="time-entry-detail",
    ),
    path("timesheets/<uuid:timesheet_id>/submit", TimesheetSubmitView.as_view(), name="timesheet-submit"),
]
