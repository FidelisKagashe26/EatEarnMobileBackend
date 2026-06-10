from rest_framework import serializers

from .models import ApprovalRequest


class ApprovalRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    applicantName = serializers.CharField(source="applicant_name")
    submittedAt = serializers.DateTimeField(source="submitted_at", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = ["id", "type", "applicantName", "details", "submittedAt", "status"]
