from django.conf import settings
from django.db import models


class ApprovalRequest(models.Model):
    class Type(models.TextChoices):
        VENDOR = "vendor", "Vendor"
        DELIVERY = "delivery", "Delivery"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    type = models.CharField(max_length=20, choices=Type.choices)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_requests",
    )
    applicant_name = models.CharField(max_length=160)
    details = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.applicant_name} ({self.type} - {self.status})"
