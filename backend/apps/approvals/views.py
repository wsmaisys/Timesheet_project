from datetime import date

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.timesheets.models import Timesheet
from apps.timesheets.serializers import TimesheetSerializer, VersionedActionSerializer
from common.concurrency import make_etag
from common.exceptions import DomainError
from common.idempotency import run_idempotent
from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser

from .serializers import DecisionSerializer
from .services import (
    approve_timesheet,
    pending_approvals_queryset,
    reject_timesheet,
    reopen_timesheet,
)


class PendingApprovalsListView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Approvals"],
        operation_id="listPendingApprovals",
        parameters=[
            OpenApiParameter("user_id", str),
            OpenApiParameter("period_start", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: TimesheetSerializer(many=True)},
    )
    def get(self, request):
        qs = pending_approvals_queryset(request.user)
        if uid := request.query_params.get("user_id"):
            qs = qs.filter(user_id=uid)
        if ps := request.query_params.get("period_start"):
            try:
                qs = qs.filter(period_start=date.fromisoformat(ps))
            except ValueError:
                raise DomainError("VALIDATION_ERROR", "Invalid period_start date. Use YYYY-MM-DD.")

        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(TimesheetSerializer(page, many=True).data)


class ApproveTimesheetView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Approvals"],
        operation_id="approveTimesheet",
        request=VersionedActionSerializer,
        responses={200: TimesheetSerializer},
    )
    def post(self, request, timesheet_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)

        def _execute():
            serializer = VersionedActionSerializer(data=request.data or {})
            serializer.is_valid(raise_exception=True)
            approved = approve_timesheet(
                actor=request.user,
                request=request,
                timesheet=ts,
                expected_version=serializer.validated_data.get("version"),
            )
            resp = Response(TimesheetSerializer(approved).data, status=200)
            resp["ETag"] = make_etag("timesheet", approved.id, approved.version)
            return resp

        return run_idempotent(request, _execute)


class RejectTimesheetView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Approvals"],
        operation_id="rejectTimesheet",
        request=DecisionSerializer,
        responses={200: TimesheetSerializer},
    )
    def post(self, request, timesheet_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)
        serializer = DecisionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        rejected = reject_timesheet(
            actor=request.user,
            request=request,
            timesheet=ts,
            reason=serializer.validated_data.get("reason"),
            expected_version=serializer.validated_data.get("version"),
        )
        resp = Response(TimesheetSerializer(rejected).data, status=200)
        resp["ETag"] = make_etag("timesheet", rejected.id, rejected.version)
        return resp


class ReopenTimesheetView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Approvals"],
        operation_id="reopenTimesheet",
        request=DecisionSerializer,
        responses={200: TimesheetSerializer},
    )
    def post(self, request, timesheet_id):
        ts = get_object_or_404(Timesheet, id=timesheet_id)
        serializer = DecisionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        reopened = reopen_timesheet(
            actor=request.user,
            request=request,
            timesheet=ts,
            reason=serializer.validated_data.get("reason"),
            expected_version=serializer.validated_data.get("version"),
        )
        resp = Response(TimesheetSerializer(reopened).data, status=200)
        resp["ETag"] = make_etag("timesheet", reopened.id, reopened.version)
        return resp
