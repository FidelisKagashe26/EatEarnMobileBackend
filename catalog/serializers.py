from rest_framework import serializers

from .models import MenuItem, Vendor


class VendorSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    etaMinutes = serializers.IntegerField(source="eta_minutes", required=False)
    isOpen = serializers.BooleanField(source="is_open", required=False)
    imageUrl = serializers.CharField(source="image_url", required=False, allow_blank=True)
    rating = serializers.FloatField(required=False)
    commissionPercent = serializers.IntegerField(source="commission_percent", required=False)
    deliverySharePercent = serializers.IntegerField(source="delivery_share_percent", required=False)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "cuisine",
            "location",
            "etaMinutes",
            "rating",
            "isOpen",
            "imageUrl",
            "latitude",
            "longitude",
            "commissionPercent",
            "deliverySharePercent",
        ]


class MenuItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    vendorId = serializers.CharField(source="vendor_id")
    isAvailable = serializers.BooleanField(source="is_available", required=False)
    imageUrl = serializers.CharField(source="image_url", required=False, allow_blank=True)

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "vendorId",
            "name",
            "description",
            "category",
            "price",
            "isAvailable",
            "imageUrl",
        ]

    def validate_vendorId(self, value):
        if not Vendor.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Vendor not found.")
        return value
