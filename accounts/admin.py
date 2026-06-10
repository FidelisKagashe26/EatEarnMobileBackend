from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import EmailOTP, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "role", "is_verified", "is_staff"]
    list_filter = ["role", "is_verified", "is_staff", "is_active"]
    search_fields = ["email", "full_name", "phone"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "role", "vendor")}),
        ("Student", {"fields": ("student_id", "department", "hostel_block")}),
        ("Vendor", {"fields": ("cafeteria_name", "business_tag")}),
        ("Delivery", {"fields": ("delivery_mode", "pickup_zone")}),
        ("Location", {"fields": ("latitude", "longitude")}),
        ("Status", {"fields": ("is_verified", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ["user", "code", "purpose", "is_used", "created_at", "expires_at"]
    list_filter = ["purpose", "is_used"]
