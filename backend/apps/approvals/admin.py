from django.contrib import admin

from .models import ApprovalEvent


@admin.register(ApprovalEvent)
class ApprovalEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "timesheet", "actor", "reason")
    list_filter = ("action",)
    search_fields = ("timesheet__user__email", "actor__email", "reason")
    readonly_fields = [f.name for f in ApprovalEvent._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
