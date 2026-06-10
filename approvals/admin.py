from django.contrib import admin

from .models import ApprovalRequest


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["applicant_name", "type", "status", "submitted_at"]
    list_filter = ["type", "status"]
    search_fields = ["applicant_name", "details"]
