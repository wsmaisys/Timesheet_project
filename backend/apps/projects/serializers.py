from rest_framework import serializers

from .models import Project, Task


class ProjectSerializer(serializers.ModelSerializer):
    client_id = serializers.UUIDField(read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    project_manager_id = serializers.UUIDField(allow_null=True, read_only=True)
    budget_hours = serializers.FloatField(allow_null=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "client_id",
            "client_name",
            "code",
            "name",
            "description",
            "start_date",
            "end_date",
            "status",
            "project_manager_id",
            "billable_default",
            "budget_hours",
            "version",
        )
        read_only_fields = fields


class ProjectCreateSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    code = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Project.Status.choices, required=False, default=Project.Status.ACTIVE)
    project_manager_id = serializers.UUIDField(required=False, allow_null=True)
    billable_default = serializers.BooleanField()
    budget_hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )


class ProjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Project.Status.choices, required=False)
    project_manager_id = serializers.UUIDField(required=False, allow_null=True)
    billable_default = serializers.BooleanField(required=False)
    budget_hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )
    version = serializers.IntegerField(min_value=1, required=False)


class TaskSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "project_id",
            "code",
            "name",
            "status",
            "sap_workstream",
            "sap_module",
        )
        read_only_fields = fields


class TaskCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=255)
    sap_workstream = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True)
    sap_module = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True)


class TaskUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    sap_workstream = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True)
    sap_module = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True)
