from datetime import date

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import DomainError
from common.permissions import CanViewReports, IsActiveUser

from .serializers import DashboardSummarySerializer, ReportRowSerializer
from .services import build_dashboard_summary, build_time_summary, export_time_summary_csv


def _parse_report_filters(request):
    params = request.query_params
    from_raw = params.get("from_date")
    to_raw = params.get("to_date")
    if not from_raw or not to_raw:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="from_date and to_date query parameters are required.",
            details=[{"field": "from_date", "issue": "required"}],
        )
    try:
        from_date = date.fromisoformat(from_raw)
        to_date = date.fromisoformat(to_raw)
    except ValueError:
        raise DomainError("VALIDATION_ERROR", "from_date and to_date must use YYYY-MM-DD format.")

    billable_raw = params.get("billable")
    billable = None
    if billable_raw is not None:
        if billable_raw.lower() == "true":
            billable = True
        elif billable_raw.lower() == "false":
            billable = False
        else:
            raise DomainError("VALIDATION_ERROR", "billable must be 'true' or 'false'.")

    return {
        "from_date": from_date,
        "to_date": to_date,
        "project_id": params.get("project_id") or None,
        "user_id": params.get("user_id") or None,
        "billable": billable,
        "status": params.get("status") or None,
    }


class TimeSummaryReportView(APIView):
    permission_classes = (CanViewReports,)

    @extend_schema(
        tags=["Reports"],
        operation_id="getTimeSummary",
        parameters=[
            OpenApiParameter("from_date", str, required=True),
            OpenApiParameter("to_date", str, required=True),
            OpenApiParameter("project_id", str),
            OpenApiParameter("user_id", str),
            OpenApiParameter("billable", bool),
            OpenApiParameter("status", str),
        ],
        responses={200: ReportRowSerializer(many=True)},
    )
    def get(self, request):
        filters = _parse_report_filters(request)
        rows = build_time_summary(actor=request.user, **filters)
        return Response(rows, status=200)


class TimeSummaryExportView(APIView):
    permission_classes = (CanViewReports,)

    @extend_schema(
        tags=["Reports"],
        operation_id="exportTimeSummary",
        parameters=[
            OpenApiParameter("from_date", str, required=True),
            OpenApiParameter("to_date", str, required=True),
            OpenApiParameter("project_id", str),
            OpenApiParameter("user_id", str),
            OpenApiParameter("billable", bool),
            OpenApiParameter("status", str),
        ],
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
    def get(self, request):
        filters = _parse_report_filters(request)
        csv_content = export_time_summary_csv(actor=request.user, **filters)
        filename = f"time-summary-{filters['from_date']}-to-{filters['to_date']}.csv"
        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DashboardView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Dashboard"],
        operation_id="getDashboard",
        responses={200: DashboardSummarySerializer},
    )
    def get(self, request):
        return Response(build_dashboard_summary(request.user), status=200)
