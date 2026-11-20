from django.contrib import admin

from .models import ProjectAssignment


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "start_date", "end_date", "allocation_percent")
    list_filter = ("project",)
    search_fields = ("user__email", "user__full_name", "project__code")
