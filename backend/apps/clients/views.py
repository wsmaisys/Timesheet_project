from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import DomainError
from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser, IsAdmin

from .models import Client
from .serializers import ClientCreateSerializer, ClientSerializer, ClientUpdateSerializer
from .services import create_client, update_client


class ClientListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsActiveUser()]

    @extend_schema(
        tags=["Clients"],
        operation_id="listClients",
        parameters=[
            OpenApiParameter("status", str, enum=["ACTIVE", "INACTIVE"]),
            OpenApiParameter("search", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: ClientSerializer(many=True)},
    )
    def get(self, request):
        qs = Client.objects.all()
        if status_param := request.query_params.get("status"):
            if status_param not in Client.Status.values:
                raise DomainError("VALIDATION_ERROR", "Invalid client status filter.")
            qs = qs.filter(status=status_param)
        if search := request.query_params.get("search"):
            term = search.strip()
            if term:
                qs = qs.filter(Q(code__icontains=term) | Q(name__icontains=term))

        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = ClientSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Clients"],
        operation_id="createClient",
        request=ClientCreateSerializer,
        responses={201: ClientSerializer},
    )
    def post(self, request):
        serializer = ClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = create_client(actor=request.user, **serializer.validated_data)
        return Response(ClientSerializer(client).data, status=201)


class ClientDetailView(APIView):
    permission_classes = (IsAdmin,)

    @extend_schema(
        tags=["Clients"],
        operation_id="updateClient",
        request=ClientUpdateSerializer,
        responses={200: ClientSerializer},
    )
    def patch(self, request, client_id):
        client = get_object_or_404(Client, id=client_id)
        serializer = ClientUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_client(actor=request.user, client=client, updates=serializer.validated_data)
        return Response(ClientSerializer(updated).data, status=200)
