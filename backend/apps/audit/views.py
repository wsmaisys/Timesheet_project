from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView

from common.exceptions import DomainError
from common.pagination import LimitOffsetMetaPagination
from common.permissions import CanViewAudit

from .models import AuditEvent
from .serializers import AuditEventSerializer


class AuditEventListView(ListAPIView):
    permission_classes = (CanViewAudit,)
    serializer_class = AuditEventSerializer
    pagination_class = LimitOffsetMetaPagination

    def get_queryset(self):
        qs = AuditEvent.objects.select_related("actor").all()
        params = self.request.query_params

        if entity_type := params.get("entity_type"):
            qs = qs.filter(entity_type=entity_type.strip())
        if entity_id := params.get("entity_id"):
            qs = qs.filter(entity_id=entity_id.strip())
        if actor_id := params.get("actor_id"):
            qs = qs.filter(actor_id=actor_id.strip())
        if action := params.get("action"):
            qs = qs.filter(action=action.strip())

        from_date_raw = params.get("from_date")
        to_date_raw = params.get("to_date")
        if from_date_raw:
            try:
                from_dt = date.fromisoformat(from_date_raw)
            except ValueError:
                raise DomainError("VALIDATION_ERROR", "Invalid from_date format. Use YYYY-MM-DD.")
            qs = qs.filter(created_at__date__gte=from_dt)
        if to_date_raw:
            try:
                to_dt = date.fromisoformat(to_date_raw)
            except ValueError:
                raise DomainError("VALIDATION_ERROR", "Invalid to_date format. Use YYYY-MM-DD.")
            qs = qs.filter(created_at__date__lte=to_dt)

        return qs

    @extend_schema(
        tags=["Audit"],
        operation_id="listAuditEvents",
        parameters=[
            OpenApiParameter("entity_type", str),
            OpenApiParameter("entity_id", str),
            OpenApiParameter("actor_id", str),
            OpenApiParameter("action", str),
            OpenApiParameter("from_date", str),
            OpenApiParameter("to_date", str),
        ],
        responses={200: AuditEventSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
