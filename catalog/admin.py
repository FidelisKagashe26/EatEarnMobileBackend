from django.contrib import admin

from .models import MenuItem, Vendor


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "cuisine", "location", "rating", "is_open"]
    list_filter = ["is_open"]
    search_fields = ["name", "cuisine", "location"]
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ["name", "vendor", "category", "price", "is_available"]
    list_filter = ["category", "is_available", "vendor"]
    search_fields = ["name", "description"]
