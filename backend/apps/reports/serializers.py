from rest_framework import serializers


class ReportRowSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    employee_code = serializers.CharField()
    employee_name = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    project_id = serializers.UUIDField()
    project_code = serializers.CharField()
    project_name = serializers.CharField()
    billable_minutes = serializers.IntegerField()
    non_billable_minutes = serializers.IntegerField()
    total_minutes = serializers.IntegerField()


class DashboardSummarySerializer(serializers.Serializer):
    role = serializers.CharField()
    current_period = serializers.DictField()
    employee_summary = serializers.DictField(allow_null=True)
    manager_summary = serializers.DictField(allow_null=True)
    admin_summary = serializers.DictField(allow_null=True)
    management_summary = serializers.DictField(allow_null=True)
    metric_definitions = serializers.DictField()
