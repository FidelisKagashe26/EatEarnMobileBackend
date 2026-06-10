from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "user_role", "is_read", "created_at"]
    list_filter = ["user_role", "is_read"]
    search_fields = ["title", "body"]
