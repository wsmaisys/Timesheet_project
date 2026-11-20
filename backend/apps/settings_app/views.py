from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsActiveUser, IsAdmin

from .serializers import CompanySettingsSerializer
from .services import get_settings, update_settings


class CompanySettingsView(APIView):
    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAdmin()]
        return [IsActiveUser()]

    @extend_schema(
        tags=["Settings"],
        operation_id="getCompanySettings",
        responses={200: CompanySettingsSerializer},
    )
    def get(self, request):
        return Response(get_settings(), status=200)

    @extend_schema(
        tags=["Settings"],
        operation_id="updateCompanySettings",
        request=CompanySettingsSerializer(partial=True),
        responses={200: CompanySettingsSerializer},
    )
    def patch(self, request):
        serializer = CompanySettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_settings(actor=request.user, updates=serializer.validated_data)
        return Response(updated, status=200)
