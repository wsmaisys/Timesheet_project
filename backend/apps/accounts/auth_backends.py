"""Authentication backends and enterprise OIDC/SAML adapter boundary."""

from dataclasses import dataclass
from typing import Protocol

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings

from common.exceptions import DomainError


class ActiveJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.auth_backends.ActiveJWTAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }


class ActiveJWTAuthentication(JWTAuthentication):
    """JWT authentication that immediately blocks deactivated accounts (FR-USER-002)."""

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken("Token contained no recognizable user identification.")

        user = self.user_model.objects.filter(**{api_settings.USER_ID_FIELD: user_id}).first()
        if user is None:
            raise AuthenticationFailed("User not found.", code="user_not_found")

        if not user.is_active or user.status != "ACTIVE":
            raise DomainError(
                code="AUTH_ACCOUNT_DISABLED",
                message="Account is inactive.",
                status_code=403,
            )

        return user


@dataclass(frozen=True)
class ExternalIdentityClaims:
    subject: str
    email: str
    full_name: str
    employee_code: str | None = None
    department: str | None = None


class OIDCIdentityAdapter(Protocol):
    """Adapter boundary for Microsoft Entra ID, SAP IAS, or other OIDC providers."""

    def verify_id_token(self, raw_token: str) -> ExternalIdentityClaims:
        ...
