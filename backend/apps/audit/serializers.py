from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor_id",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "before_json",
            "after_json",
            "request_id",
            "created_at",
        )
        read_only_fields = fields
