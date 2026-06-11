from django.db import models


class Vendor(models.Model):
    """A campus cafeteria / food vendor."""

    name = models.CharField(max_length=120)
    cuisine = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=160, blank=True)
    eta_minutes = models.PositiveIntegerField(default=15)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    is_open = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)

    # Map coordinates (campus point)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Money split, set by the admin when registering the vendor:
    # - commission_percent: % of each order's subtotal the platform takes.
    # - delivery_share_percent: % OF THAT COMMISSION paid to the delivery agent.
    commission_percent = models.PositiveSmallIntegerField(default=10)
    delivery_share_percent = models.PositiveSmallIntegerField(default=40)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_open", "-rating", "name"]

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="menu_items")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=60, blank=True)
    price = models.PositiveIntegerField(default=0)  # whole TZS
    is_available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.vendor.name})"
