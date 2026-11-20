from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "user_id",
            "type",
            "title",
            "payload",
            "read_at",
            "delivery_status",
            "created_at",
        )
        read_only_fields = fields
