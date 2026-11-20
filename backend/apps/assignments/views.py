from datetime import date

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import DomainError
from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser

from .models import ProjectAssignment
from .serializers import AssignmentCreateSerializer, AssignmentSerializer, AssignmentUpdateSerializer
from .services import create_assignment, scoped_assignments_queryset, update_assignment


class AssignmentListCreateView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Assignments"],
        operation_id="listAssignments",
        parameters=[
            OpenApiParameter("user_id", str),
            OpenApiParameter("project_id", str),
            OpenApiParameter("active_on", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: AssignmentSerializer(many=True)},
    )
    def get(self, request):
        qs = scoped_assignments_queryset(request.user)
        if user_id := request.query_params.get("user_id"):
            qs = qs.filter(user_id=user_id)
        if project_id := request.query_params.get("project_id"):
            qs = qs.filter(project_id=project_id)
        if active_on_raw := request.query_params.get("active_on"):
            try:
                active_on = date.fromisoformat(active_on_raw)
            except ValueError:
                raise DomainError("VALIDATION_ERROR", "Invalid active_on date format. Use YYYY-MM-DD.")
            qs = qs.filter(start_date__lte=active_on).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=active_on)
            )

        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(AssignmentSerializer(page, many=True).data)

    @extend_schema(
        tags=["Assignments"],
        operation_id="createAssignment",
        request=AssignmentCreateSerializer,
        responses={201: AssignmentSerializer},
    )
    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = create_assignment(actor=request.user, payload=serializer.validated_data)
        return Response(AssignmentSerializer(assignment).data, status=201)


class AssignmentDetailView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Assignments"],
        operation_id="updateAssignment",
        request=AssignmentUpdateSerializer,
        responses={200: AssignmentSerializer},
    )
    def patch(self, request, assignment_id):
        assignment = get_object_or_404(ProjectAssignment.objects.select_related("project", "user"), id=assignment_id)
        serializer = AssignmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_assignment(
            actor=request.user,
            assignment=assignment,
            payload=serializer.validated_data,
        )
        return Response(AssignmentSerializer(updated).data, status=200)
