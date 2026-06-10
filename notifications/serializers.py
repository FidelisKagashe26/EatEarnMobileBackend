from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    userRole = serializers.CharField(source="user_role", required=False, allow_blank=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    isRead = serializers.BooleanField(source="is_read", required=False)

    class Meta:
        model = Notification
        fields = ["id", "userRole", "title", "body", "createdAt", "isRead"]
