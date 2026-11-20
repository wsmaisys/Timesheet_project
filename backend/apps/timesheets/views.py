from datetime import date

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.concurrency import make_etag
from common.exceptions import DomainError
from common.idempotency import run_idempotent
from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser

from .models import TimeEntry, Timesheet
from .serializers import (
    TimeEntryCreateSerializer,
    TimeEntryPatchSerializer,
    TimeEntrySerializer,
    TimesheetCreateSerializer,
    TimesheetPatchSerializer,
    TimesheetSerializer,
    VersionedActionSerializer,
)
from .services import (
    add_time_entry,
    create_timesheet,
    delete_time_entry,
    scoped_timesheets_queryset,
    submit_timesheet,
    update_time_entry,
    update_timesheet,
)


def _get_accessible_timesheet(actor, timesheet_id) -> Timesheet:
    ts = get_object_or_404(Timesheet, id=timesheet_id)
    scoped = scoped_timesheets_queryset(actor).filter(id=ts.id).first()
    if scoped is None:
        raise DomainError("AUTH_FORBIDDEN", "You do not have access to this timesheet.", status_code=403)
    return scoped


class TimesheetListCreateView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="listTimesheets",
        parameters=[
            OpenApiParameter("status", str, enum=Timesheet.Status.values),
            OpenApiParameter("period_start", str),
            OpenApiParameter("period_end", str),
            OpenApiParameter("user_id", str),
            OpenApiParameter("project_id", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: TimesheetSerializer(many=True)},
    )
    def get(self, request):
        qs = scoped_timesheets_queryset(request.user)
        params = request.query_params

        if status_param := params.get("status"):
            if status_param not in Timesheet.Status.values:
                raise DomainError("VALIDATION_ERROR", "Invalid timesheet status filter.")
            qs = qs.filter(status=status_param)
        if ps := params.get("period_start"):
            try:
                qs = qs.filter(period_start__gte=date.fromisoformat(ps))
            except ValueError:
                raise DomainError("VALIDATION_ERROR", "Invalid period_start date. Use YYYY-MM-DD.")
        if pe := params.get("period_end"):
            try:
                qs = qs.filter(period_end__lte=date.fromisoformat(pe))
            except ValueError:
                raise DomainError("VALIDATION_ERROR", "Invalid period_end date. Use YYYY-MM-DD.")
        if uid := params.get("user_id"):
            qs = qs.filter(user_id=uid)
        if pid := params.get("project_id"):
            qs = qs.filter(entries__project_id=pid).distinct()

        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(TimesheetSerializer(page, many=True).data)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="createTimesheet",
        request=TimesheetCreateSerializer,
        responses={201: TimesheetSerializer},
    )
    def post(self, request):
        def _execute():
            serializer = TimesheetCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            ts = create_timesheet(actor=request.user, **serializer.validated_data)
            resp = Response(TimesheetSerializer(ts).data, status=201)
            resp["ETag"] = make_etag("timesheet", ts.id, ts.version)
            return resp

        return run_idempotent(request, _execute)


class TimesheetDetailView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="getTimesheet",
        responses={200: TimesheetSerializer},
    )
    def get(self, request, timesheet_id):
        ts = _get_accessible_timesheet(request.user, timesheet_id)
        resp = Response(TimesheetSerializer(ts).data, status=200)
        resp["ETag"] = make_etag("timesheet", ts.id, ts.version)
        return resp

    @extend_schema(
        tags=["Timesheets"],
        operation_id="updateTimesheet",
        request=TimesheetPatchSerializer,
        responses={200: TimesheetSerializer},
    )
    def patch(self, request, timesheet_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)
        serializer = TimesheetPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_timesheet(
            actor=request.user,
            request=request,
            timesheet=ts,
            payload=serializer.validated_data,
        )
        resp = Response(TimesheetSerializer(updated).data, status=200)
        resp["ETag"] = make_etag("timesheet", updated.id, updated.version)
        return resp


class TimeEntryCreateView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="addTimeEntry",
        request=TimeEntryCreateSerializer,
        responses={201: TimeEntrySerializer},
    )
    def post(self, request, timesheet_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)

        def _execute():
            serializer = TimeEntryCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            entry = add_time_entry(actor=request.user, timesheet=ts, payload=serializer.validated_data)
            return Response(TimeEntrySerializer(entry).data, status=201)

        return run_idempotent(request, _execute)


class TimeEntryDetailView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="updateTimeEntry",
        request=TimeEntryPatchSerializer,
        responses={200: TimeEntrySerializer},
    )
    def patch(self, request, timesheet_id, entry_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)
        entry = get_object_or_404(TimeEntry, id=entry_id)
        serializer = TimeEntryPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_time_entry(
            actor=request.user,
            timesheet=ts,
            entry=entry,
            payload=serializer.validated_data,
        )
        return Response(TimeEntrySerializer(updated).data, status=200)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="deleteTimeEntry",
        responses={204: None},
    )
    def delete(self, request, timesheet_id, entry_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)
        entry = get_object_or_404(TimeEntry, id=entry_id)
        delete_time_entry(actor=request.user, timesheet=ts, entry=entry)
        return Response(status=204)


class TimesheetSubmitView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Timesheets"],
        operation_id="submitTimesheet",
        request=VersionedActionSerializer,
        responses={200: TimesheetSerializer},
    )
    def post(self, request, timesheet_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)

        def _execute():
            serializer = VersionedActionSerializer(data=request.data or {})
            serializer.is_valid(raise_exception=True)
            submitted = submit_timesheet(
                actor=request.user,
                request=request,
                timesheet=ts,
                expected_version=serializer.validated_data.get("version"),
            )
            resp = Response(TimesheetSerializer(submitted).data, status=200)
            resp["ETag"] = make_etag("timesheet", submitted.id, submitted.version)
            return resp

        return run_idempotent(request, _execute)
