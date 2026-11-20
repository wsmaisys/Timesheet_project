from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import DomainError
from common.pagination import LimitOffsetMetaPagination
from common.permissions import IsActiveUser, IsAdmin

from .models import User
from .permissions import get_effective_permissions
from .serializers import (
    CurrentUserSerializer,
    LoginRequestSerializer,
    LogoutRequestSerializer,
    TokenRefreshRequestSerializer,
    TokenRefreshResponseSerializer,
    TokenResponseSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services import create_user, update_user


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get_throttles(self):
        if not drf_api_settings.DEFAULT_THROTTLE_CLASSES:
            return []
        return [LoginRateThrottle()]

    @extend_schema(
        tags=["Auth"],
        operation_id="authLogin",
        request=LoginRequestSerializer,
        responses={200: TokenResponseSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.check_password(password):
            raise DomainError(
                code="AUTH_INVALID_CREDENTIALS",
                message="Invalid email or password.",
                status_code=401,
            )

        if not user.is_active or user.status != User.Status.ACTIVE:
            raise DomainError(
                code="AUTH_ACCOUNT_DISABLED",
                message="Account is inactive.",
                status_code=403,
            )

        user.last_login = dj_timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "permissions": get_effective_permissions(user),
            },
            status=200,
        )


class RefreshView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        tags=["Auth"],
        operation_id="authRefresh",
        request=TokenRefreshRequestSerializer,
        responses={200: TokenRefreshResponseSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = TokenRefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_refresh = serializer.validated_data["refresh"]

        try:
            old_refresh = RefreshToken(raw_refresh)
            user_id = old_refresh.get("user_id")
            user = User.objects.filter(id=user_id).first()
            if user is None:
                raise DomainError("AUTH_INVALID_TOKEN", "Invalid refresh token.", status_code=401)
            if not user.is_active or user.status != User.Status.ACTIVE:
                raise DomainError("AUTH_ACCOUNT_DISABLED", "Account is inactive.", status_code=403)

            access = str(old_refresh.access_token)
            try:
                old_refresh.blacklist()
            except AttributeError:
                pass
            new_refresh = RefreshToken.for_user(user)
        except TokenError:
            raise DomainError("AUTH_INVALID_TOKEN", "Refresh token is invalid or expired.", status_code=401)

        return Response({"access": access, "refresh": str(new_refresh)}, status=200)


class LogoutView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Auth"],
        operation_id="authLogout",
        request=LogoutRequestSerializer,
        responses={204: None},
    )
    def post(self, request):
        raw_refresh = (request.data or {}).get("refresh")
        if raw_refresh:
            try:
                token = RefreshToken(raw_refresh)
                token.blacklist()
            except (TokenError, AttributeError):
                pass
        return Response(status=204)


class CurrentUserView(APIView):
    permission_classes = (IsActiveUser,)

    @extend_schema(
        tags=["Identity"],
        operation_id="getCurrentUser",
        responses={200: CurrentUserSerializer},
    )
    def get(self, request):
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "permissions": get_effective_permissions(request.user),
            },
            status=200,
        )


class UserListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsActiveUser()]

    @extend_schema(
        tags=["Users"],
        operation_id="listUsers",
        parameters=[
            OpenApiParameter("role", str, enum=User.Role.values),
            OpenApiParameter("status", str, enum=User.Status.values),
            OpenApiParameter("department", str),
            OpenApiParameter("search", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("offset", int),
        ],
        responses={200: UserSerializer(many=True)},
    )
    def get(self, request):
        user = request.user
        if user.role == User.Role.ADMIN:
            qs = User.objects.all()
        elif user.role == User.Role.APPROVER:
            qs = User.objects.filter(Q(id=user.id) | Q(manager_id=user.id))
        else:
            raise DomainError(
                code="AUTH_FORBIDDEN",
                message="You do not have permission to list user accounts.",
                status_code=403,
            )

        if role_param := request.query_params.get("role"):
            if role_param not in User.Role.values:
                raise DomainError("VALIDATION_ERROR", "Invalid role filter.")
            qs = qs.filter(role=role_param)
        if status_param := request.query_params.get("status"):
            if status_param not in User.Status.values:
                raise DomainError("VALIDATION_ERROR", "Invalid status filter.")
            qs = qs.filter(status=status_param)
        if dept := request.query_params.get("department"):
            qs = qs.filter(department__iexact=dept.strip())
        if search := request.query_params.get("search"):
            term = search.strip()
            if term:
                qs = qs.filter(
                    Q(full_name__icontains=term)
                    | Q(email__icontains=term)
                    | Q(employee_code__icontains=term)
                )

        paginator = LimitOffsetMetaPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(UserSerializer(page, many=True).data)

    @extend_schema(
        tags=["Users"],
        operation_id="createUser",
        request=UserCreateSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = create_user(actor=request.user, payload=serializer.validated_data)
        return Response(UserSerializer(created).data, status=201)


class UserDetailView(APIView):
    permission_classes = (IsActiveUser,)

    def _get_scoped_user(self, actor: User, user_id) -> User:
        target = get_object_or_404(User, id=user_id)
        if actor.role == User.Role.ADMIN or actor.id == target.id:
            return target
        if actor.role == User.Role.APPROVER and target.manager_id == actor.id:
            return target
        raise DomainError(
            code="AUTH_FORBIDDEN",
            message="You do not have permission to access this user profile.",
            status_code=403,
        )

    @extend_schema(
        tags=["Users"],
        operation_id="getUser",
        responses={200: UserSerializer},
    )
    def get(self, request, user_id):
        target = self._get_scoped_user(request.user, user_id)
        return Response(UserSerializer(target).data, status=200)

    @extend_schema(
        tags=["Users"],
        operation_id="updateUser",
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_user(actor=request.user, target=target, payload=serializer.validated_data)
        return Response(UserSerializer(updated).data, status=200)
