from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from notifications.models import Notification

from .models import ApprovalRequest
from .serializers import ApprovalRequestSerializer


def _is_admin(user):
    return getattr(user, "role", None) == "admin" or getattr(user, "is_superuser", False)


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    queryset = ApprovalRequest.objects.select_related("applicant").all()
    serializer_class = ApprovalRequestSerializer
    # Reads are open to signed-in staff screens; writes happen only through
    # the admin-guarded `decision` action below.
    http_method_names = ["get", "patch", "head", "options"]

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied("Use the decision endpoint.")

    @action(detail=True, methods=["patch"])
    def decision(self, request, pk=None):
        # Only admins decide applications — an applicant must never be able
        # to approve themselves through the API.
        if not _is_admin(request.user):
            raise PermissionDenied("Only admins can approve or reject applications.")

        approval = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(ApprovalRequest.Status.choices):
            return Response({"detail": "status must be 'approved' or 'rejected'."}, status=400)

        approval.status = new_status
        approval.save(update_fields=["status"])

        # Reflect the decision on the applicant's account so they can operate.
        if approval.applicant_id:
            applicant = approval.applicant
            applicant.is_approved = new_status == ApprovalRequest.Status.APPROVED
            applicant.save(update_fields=["is_approved"])
            Notification.objects.create(
                user=applicant,
                user_role=applicant.role,
                title=f"Your application was {new_status}",
                body=(
                    "You can now sign in and start working."
                    if applicant.is_approved
                    else "Your application was not approved. Please contact the admin."
                ),
            )

        return Response(self.get_serializer(approval).data)
