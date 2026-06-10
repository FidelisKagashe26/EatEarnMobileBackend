from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A notification targeted at a specific user and/or a whole role."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    user_role = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
