from django.contrib import admin

from .models import CompanySetting


@admin.register(CompanySetting)
class CompanySettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "updated_by", "updated_at")
    search_fields = ("key",)
    readonly_fields = ("updated_at",)
