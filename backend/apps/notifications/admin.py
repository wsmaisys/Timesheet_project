from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "type", "user", "delivery_status", "read_at")
    list_filter = ("type", "delivery_status")
    search_fields = ("title", "user__email")
    readonly_fields = ("created_at",)
