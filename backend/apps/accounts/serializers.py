from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    manager_id = serializers.UUIDField(allow_null=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "employee_code",
            "email",
            "full_name",
            "role",
            "status",
            "manager_id",
            "department",
            "timezone",
            "expected_daily_minutes",
            "expected_weekly_minutes",
            "can_override_assignment",
        )
        read_only_fields = fields


class CurrentUserSerializer(serializers.Serializer):
    user = UserSerializer()
    permissions = serializers.ListField(child=serializers.CharField())


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    permissions = serializers.ListField(child=serializers.CharField())


class UserCreateSerializer(serializers.Serializer):
    employee_code = serializers.CharField(max_length=64)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=8, required=False, write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices)
    manager_id = serializers.UUIDField(required=False, allow_null=True)
    department = serializers.CharField(max_length=128, required=False, allow_null=True, allow_blank=True)
    timezone = serializers.CharField(max_length=64, default="UTC")
    expected_daily_minutes = serializers.IntegerField(min_value=60, max_value=1440, required=False, allow_null=True)
    expected_weekly_minutes = serializers.IntegerField(min_value=60, max_value=10080, required=False, allow_null=True)
    can_override_assignment = serializers.BooleanField(required=False, default=False)


class UserUpdateSerializer(serializers.Serializer):
    employee_code = serializers.CharField(max_length=64, required=False)
    full_name = serializers.CharField(max_length=255, required=False)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    status = serializers.ChoiceField(choices=User.Status.choices, required=False)
    manager_id = serializers.UUIDField(required=False, allow_null=True)
    department = serializers.CharField(max_length=128, required=False, allow_null=True, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False)
    expected_daily_minutes = serializers.IntegerField(min_value=60, max_value=1440, required=False, allow_null=True)
    expected_weekly_minutes = serializers.IntegerField(min_value=60, max_value=10080, required=False, allow_null=True)
    can_override_assignment = serializers.BooleanField(required=False)
