import random
import string

from django.conf import settings
from django.db import models

from catalog.models import MenuItem, Vendor


def generate_order_reference():
    return "EAT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PREPARING = "PREPARING", "Preparing"
        READY = "READY", "Ready"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    class DeliveryType(models.TextChoices):
        PICKUP = "pickup", "Pickup"
        DELIVERY = "delivery", "Delivery"

    # Human-friendly reference shown in the UI instead of the raw numeric id.
    reference = models.CharField(max_length=12, blank=True, db_index=True)

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="orders")
    delivery_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )

    subtotal = models.PositiveIntegerField(default=0)
    delivery_fee = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    payment_method = models.CharField(max_length=20, default="cash")
    delivery_type = models.CharField(
        max_length=20, choices=DeliveryType.choices, default=DeliveryType.DELIVERY
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)

    delivery_location = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Delivery agent's last-known location (for live tracking on the map).
    agent_latitude = models.FloatField(null=True, blank=True)
    agent_longitude = models.FloatField(null=True, blank=True)

    # Customer's rating (1-5) after delivery; feeds the vendor's average.
    rating = models.PositiveSmallIntegerField(null=True, blank=True)

    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-placed_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            ref = generate_order_reference()
            while Order.objects.filter(reference=ref).exists():
                ref = generate_order_reference()
            self.reference = ref
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        self.subtotal = sum(line.unit_price * line.quantity for line in self.items.all())
        self.total = self.subtotal + self.delivery_fee

    def __str__(self):
        return f"Order {self.reference or self.pk} - {self.student.email} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        MenuItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_lines"
    )
    name = models.CharField(max_length=160)
    unit_price = models.PositiveIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.name}"
