from django.contrib import admin

from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "client", "status", "start_date", "end_date", "billable_default")
    list_filter = ("status", "billable_default")
    search_fields = ("code", "name", "client__name")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "project", "status", "sap_module", "sap_workstream")
    list_filter = ("status", "sap_module", "sap_workstream")
    search_fields = ("code", "name", "project__code")
