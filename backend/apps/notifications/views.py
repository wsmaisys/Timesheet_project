from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser

from .models import Notification
from .serializers import NotificationSerializer
from .services import mark_all_read, mark_read


class MarkedReadResponseSerializer(serializers.Serializer):
    marked_count = serializers.IntegerField()


class NotificationListView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Notifications"],
        operation_id="listNotifications",
        parameters=[
            OpenApiParameter("unread_only", bool),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        if request.query_params.get("unread_only") == "true":
            qs = qs.filter(read_at__isnull=True)

        unread_count = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        resp = paginator.get_paginated_response(NotificationSerializer(page, many=True).data)
        resp.data["unread_count"] = unread_count
        return resp


class NotificationReadView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Notifications"],
        operation_id="markNotificationRead",
        request=None,
        responses={200: NotificationSerializer},
    )
    def post(self, request, notification_id):
        updated = mark_read(user=request.user, notification_id=notification_id)
        if updated is None:
            raise Http404
        return Response(NotificationSerializer(updated).data, status=200)


class NotificationReadAllView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Notifications"],
        operation_id="markAllNotificationsRead",
        request=None,
        responses={200: MarkedReadResponseSerializer},
    )
    def post(self, request):
        count = mark_all_read(user=request.user)
        return Response({"marked_count": count}, status=200)
