"""Liveness and readiness probe endpoints (SRS §18)."""

from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import build_error_payload


class HealthStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField(required=False)


class HealthLiveView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        tags=["Health"],
        operation_id="healthLive",
        responses={200: HealthStatusSerializer},
        auth=[],
    )
    def get(self, request):
        return Response({"status": "ok"}, status=200)


class HealthReadyView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        tags=["Health"],
        operation_id="healthReady",
        responses={200: HealthStatusSerializer},
        auth=[],
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response(
                build_error_payload(
                    code="INTERNAL_ERROR",
                    message="Database readiness check failed.",
                    request_id=getattr(request, "request_id", None),
                ),
                status=503,
            )
        return Response({"status": "ready", "database": "ok"}, status=200)
