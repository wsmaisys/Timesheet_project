from django.urls import path

from .views import AssignmentDetailView, AssignmentListCreateView

urlpatterns = [
    path("assignments", AssignmentListCreateView.as_view(), name="assignment-list-create"),
    path("assignments/<uuid:assignment_id>", AssignmentDetailView.as_view(), name="assignment-detail"),
]
