from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ApprovalRequest
from .serializers import ApprovalRequestSerializer


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    queryset = ApprovalRequest.objects.all()
    serializer_class = ApprovalRequestSerializer

    @action(detail=True, methods=["patch"])
    def decision(self, request, pk=None):
        approval = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(ApprovalRequest.Status.choices):
            return Response({"detail": "status must be 'approved' or 'rejected'."}, status=400)
        approval.status = new_status
        approval.save(update_fields=["status"])
        return Response(self.get_serializer(approval).data)
