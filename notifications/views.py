from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


# Read-only: notifications are created by the system (orders, approvals…),
# never by API clients — otherwise anyone could forge alerts for other roles.
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Personal notifications + anything broadcast to my role.
        return Notification.objects.filter(Q(user=user) | Q(user_role=user.role, user__isnull=True))

    @action(detail=True, methods=["patch"])
    def read(self, request, pk=None):
        note = self.get_object()
        note.is_read = True
        note.save(update_fields=["is_read"])
        return Response(self.get_serializer(note).data)

    @action(detail=False, methods=["patch"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().update(is_read=True)
        return Response({"detail": "All notifications marked as read."})
