from rest_framework import serializers


class CompanySettingsSerializer(serializers.Serializer):
    week_start_day = serializers.IntegerField(min_value=0, max_value=6)
    default_timezone = serializers.CharField(max_length=64)
    expected_daily_minutes = serializers.IntegerField(min_value=60, max_value=1440)
    expected_weekly_minutes = serializers.IntegerField(min_value=60, max_value=10080)
    entry_increment_minutes = serializers.ChoiceField(choices=[5, 6, 15, 30, 60])
    max_daily_minutes = serializers.IntegerField(min_value=60, max_value=1440)
    submission_deadline_day = serializers.IntegerField(min_value=0, max_value=6)
    submission_deadline_time = serializers.CharField(max_length=5)
    allow_billable_override = serializers.BooleanField()
    allow_duplicate_entries = serializers.BooleanField()
    allow_self_approval = serializers.BooleanField()
    allow_overlapping_assignments = serializers.BooleanField()
    require_minimum_hours_on_submit = serializers.BooleanField()
    max_export_rows = serializers.IntegerField(min_value=1, max_value=1000000)
    sap_modules = serializers.ListField(child=serializers.CharField(max_length=64), allow_empty=False)
    sap_workstreams = serializers.ListField(child=serializers.CharField(max_length=64), allow_empty=False)
