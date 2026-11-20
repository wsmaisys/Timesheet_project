from rest_framework import serializers

from .models import ProjectAssignment


class AssignmentSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    project_id = serializers.UUIDField(read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    allocation_percent = serializers.FloatField(allow_null=True, read_only=True)

    class Meta:
        model = ProjectAssignment
        fields = (
            "id",
            "user_id",
            "user_name",
            "project_id",
            "project_code",
            "project_name",
            "start_date",
            "end_date",
            "allocation_percent",
        )
        read_only_fields = fields


class AssignmentCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    allocation_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
        allow_null=True,
    )


class AssignmentUpdateSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    allocation_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
        allow_null=True,
    )
