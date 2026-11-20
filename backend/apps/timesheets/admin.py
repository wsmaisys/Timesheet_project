from django.contrib import admin

from .models import IdempotencyRecord, TimeEntry, Timesheet


class TimeEntryInline(admin.TabularInline):
    model = TimeEntry
    extra = 0
    readonly_fields = ("work_date", "project", "task", "duration_minutes", "billable", "description")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ("user", "period_start", "period_end", "status", "assigned_approver", "version")
    list_filter = ("status", "period_start")
    search_fields = ("user__email", "user__employee_code")
    readonly_fields = ("submitted_at", "approved_at", "version", "created_at", "updated_at")
    inlines = [TimeEntryInline]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("work_date", "timesheet", "project", "task", "duration_minutes", "billable")
    list_filter = ("billable", "work_date")
    search_fields = ("project__code", "task__code", "description")


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "method", "path", "key", "status_code", "created_at")
    readonly_fields = [f.name for f in IdempotencyRecord._meta.fields]
