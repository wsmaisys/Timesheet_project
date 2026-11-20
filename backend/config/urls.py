"""Root URL configuration aligned 1:1 with the OpenAPI 3.1 contract."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.exceptions import json_404_handler, json_500_handler
from common.health import HealthLiveView, HealthReadyView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/health/live", HealthLiveView.as_view(), name="health-live"),
    path("api/v1/health/ready", HealthReadyView.as_view(), name="health-ready"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.settings_app.urls")),
    path("api/v1/", include("apps.clients.urls")),
    path("api/v1/", include("apps.projects.urls")),
    path("api/v1/", include("apps.assignments.urls")),
    path("api/v1/", include("apps.timesheets.urls")),
    path("api/v1/", include("apps.approvals.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.audit.urls")),
]

handler404 = json_404_handler
handler500 = json_500_handler
