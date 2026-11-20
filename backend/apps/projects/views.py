from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.concurrency import make_etag
from common.exceptions import DomainError
from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser, IsAdmin

from .models import Project, Task
from .serializers import (
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    TaskCreateSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)
from .services import (
    create_project,
    create_task,
    scoped_projects_queryset,
    update_project,
    update_task,
)


class ProjectListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsActiveUser()]

    @extend_schema(
        tags=["Projects"],
        operation_id="listProjects",
        parameters=[
            OpenApiParameter("status", str, enum=Project.Status.values),
            OpenApiParameter("client_id", str),
            OpenApiParameter("search", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: ProjectSerializer(many=True)},
    )
    def get(self, request):
        qs = scoped_projects_queryset(request.user)
        if status_param := request.query_params.get("status"):
            if status_param not in Project.Status.values:
                raise DomainError("VALIDATION_ERROR", "Invalid project status filter.")
            qs = qs.filter(status=status_param)
        if client_id := request.query_params.get("client_id"):
            qs = qs.filter(client_id=client_id)
        if search := request.query_params.get("search"):
            term = search.strip()
            if term:
                qs = qs.filter(Q(code__icontains=term) | Q(name__icontains=term))

        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(ProjectSerializer(page, many=True).data)

    @extend_schema(
        tags=["Projects"],
        operation_id="createProject",
        request=ProjectCreateSerializer,
        responses={201: ProjectSerializer},
    )
    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_project(actor=request.user, payload=serializer.validated_data)
        resp = Response(ProjectSerializer(project).data, status=201)
        resp["ETag"] = make_etag("project", project.id, project.version)
        return resp


class ProjectDetailView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Projects"],
        operation_id="getProject",
        responses={200: ProjectSerializer},
    )
    def get(self, request, project_id):
        project = get_object_or_404(Project.objects.select_related("client"), id=project_id)
        if not scoped_projects_queryset(request.user).filter(id=project.id).exists():
            raise DomainError("AUTH_FORBIDDEN", "You do not have access to this project.", status_code=403)
        resp = Response(ProjectSerializer(project).data, status=200)
        resp["ETag"] = make_etag("project", project.id, project.version)
        return resp

    @extend_schema(
        tags=["Projects"],
        operation_id="updateProject",
        request=ProjectUpdateSerializer,
        responses={200: ProjectSerializer},
    )
    def patch(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        serializer = ProjectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_project(
            actor=request.user,
            request=request,
            project=project,
            payload=serializer.validated_data,
        )
        resp = Response(ProjectSerializer(updated).data, status=200)
        resp["ETag"] = make_etag("project", updated.id, updated.version)
        return resp


class ProjectTaskListCreateView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Projects"],
        operation_id="listProjectTasks",
        parameters=[OpenApiParameter("status", str, enum=Task.Status.values)],
        responses={200: TaskSerializer(many=True)},
    )
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        if not scoped_projects_queryset(request.user).filter(id=project.id).exists():
            raise DomainError("AUTH_FORBIDDEN", "You do not have access to this project.", status_code=403)

        qs = Task.objects.filter(project=project)
        if status_param := request.query_params.get("status"):
            if status_param not in Task.Status.values:
                raise DomainError("VALIDATION_ERROR", "Invalid task status filter.")
            qs = qs.filter(status=status_param)
        return Response(TaskSerializer(qs, many=True).data, status=200)

    @extend_schema(
        tags=["Projects"],
        operation_id="createProjectTask",
        request=TaskCreateSerializer,
        responses={201: TaskSerializer},
    )
    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = create_task(actor=request.user, project=project, payload=serializer.validated_data)
        return Response(TaskSerializer(task).data, status=201)


class ProjectTaskDetailView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Projects"],
        operation_id="updateProjectTask",
        request=TaskUpdateSerializer,
        responses={200: TaskSerializer},
    )
    def patch(self, request, project_id, task_id):
        project = get_object_or_404(Project, id=project_id)
        task = get_object_or_404(Task, id=task_id, project=project)
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_task(actor=request.user, project=project, task=task, payload=serializer.validated_data)
        return Response(TaskSerializer(updated).data, status=200)
