from django.urls import path

from .views import (
    ProjectDetailView,
    ProjectListCreateView,
    ProjectTaskDetailView,
    ProjectTaskListCreateView,
)

urlpatterns = [
    path("projects", ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<uuid:project_id>", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<uuid:project_id>/tasks", ProjectTaskListCreateView.as_view(), name="project-task-list-create"),
    path(
        "projects/<uuid:project_id>/tasks/<uuid:task_id>",
        ProjectTaskDetailView.as_view(),
        name="project-task-detail",
    ),
]
