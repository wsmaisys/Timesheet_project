from django.urls import path

from .views import DashboardView, TimeSummaryExportView, TimeSummaryReportView

urlpatterns = [
    path("reports/time-summary", TimeSummaryReportView.as_view(), name="report-time-summary"),
    path("reports/time-summary/export", TimeSummaryExportView.as_view(), name="report-time-summary-export"),
    path("dashboard", DashboardView.as_view(), name="dashboard"),
]
