from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "student", "vendor", "status", "delivery_type", "total", "placed_at"]
    list_filter = ["status", "delivery_type"]
    search_fields = ["id", "student__email", "vendor__name"]
    inlines = [OrderItemInline]
