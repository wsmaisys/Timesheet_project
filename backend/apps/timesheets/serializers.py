from rest_framework import serializers

from apps.approvals.models import ApprovalEvent

from .models import TimeEntry, Timesheet


class TimeEntrySerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    task_id = serializers.UUIDField(read_only=True)
    task_code = serializers.CharField(source="task.code", read_only=True)
    task_name = serializers.CharField(source="task.name", read_only=True)
    sap_module = serializers.CharField(source="task.sap_module", read_only=True, allow_null=True)
    sap_workstream = serializers.CharField(source="task.sap_workstream", read_only=True, allow_null=True)

    class Meta:
        model = TimeEntry
        fields = (
            "id",
            "work_date",
            "project_id",
            "project_code",
            "project_name",
            "task_id",
            "task_code",
            "task_name",
            "sap_module",
            "sap_workstream",
            "duration_minutes",
            "billable",
            "description",
        )
        read_only_fields = fields


class ApprovalEventInlineSerializer(serializers.ModelSerializer):
    timesheet_id = serializers.UUIDField(read_only=True)
    actor_id = serializers.UUIDField(read_only=True)
    actor_name = serializers.CharField(source="actor.full_name", read_only=True)

    class Meta:
        model = ApprovalEvent
        fields = ("id", "timesheet_id", "actor_id", "actor_name", "action", "reason", "created_at")
        read_only_fields = fields


class TimesheetSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    employee_code = serializers.CharField(source="user.employee_code", read_only=True)
    assigned_approver_id = serializers.UUIDField(allow_null=True, read_only=True)
    total_minutes = serializers.SerializerMethodField()
    billable_minutes = serializers.SerializerMethodField()
    entries = TimeEntrySerializer(many=True, read_only=True)
    approval_events = ApprovalEventInlineSerializer(many=True, read_only=True)

    class Meta:
        model = Timesheet
        fields = (
            "id",
            "user_id",
            "user_name",
            "employee_code",
            "period_start",
            "period_end",
            "status",
            "notes",
            "assigned_approver_id",
            "total_minutes",
            "billable_minutes",
            "entries",
            "approval_events",
            "submitted_at",
            "approved_at",
            "version",
        )
        read_only_fields = fields

    def get_total_minutes(self, obj: Timesheet) -> int:
        return sum(e.duration_minutes for e in obj.entries.all())

    def get_billable_minutes(self, obj: Timesheet) -> int:
        return sum(e.duration_minutes for e in obj.entries.all() if e.billable)


class TimesheetCreateSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)


class TimesheetPatchSerializer(serializers.Serializer):
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)
    version = serializers.IntegerField(min_value=1, required=False)


class TimeEntryCreateSerializer(serializers.Serializer):
    work_date = serializers.DateField()
    project_id = serializers.UUIDField()
    task_id = serializers.UUIDField()
    duration_minutes = serializers.IntegerField(min_value=1)
    billable = serializers.BooleanField()
    description = serializers.CharField(min_length=1, max_length=1000, trim_whitespace=False)


class TimeEntryPatchSerializer(serializers.Serializer):
    work_date = serializers.DateField(required=False)
    project_id = serializers.UUIDField(required=False)
    task_id = serializers.UUIDField(required=False)
    duration_minutes = serializers.IntegerField(min_value=1, required=False)
    billable = serializers.BooleanField(required=False)
    description = serializers.CharField(min_length=1, max_length=1000, trim_whitespace=False, required=False)


class VersionedActionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1, required=False)
