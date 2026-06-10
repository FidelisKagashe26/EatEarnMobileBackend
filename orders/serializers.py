from django.db import transaction
from rest_framework import serializers

from catalog.models import MenuItem, Vendor

from .models import Order, OrderItem

DELIVERY_FEE = 1000  # flat TZS delivery fee


class OrderItemSerializer(serializers.ModelSerializer):
    menuItemId = serializers.SerializerMethodField()
    unitPrice = serializers.IntegerField(source="unit_price")

    class Meta:
        model = OrderItem
        fields = ["menuItemId", "name", "unitPrice", "quantity"]

    def get_menuItemId(self, obj):
        return str(obj.menu_item_id) if obj.menu_item_id else None


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    studentId = serializers.CharField(source="student_id", read_only=True)
    studentName = serializers.CharField(source="student.full_name", read_only=True)
    studentPhone = serializers.CharField(source="student.phone", read_only=True)
    vendorId = serializers.CharField(source="vendor_id", read_only=True)
    vendorName = serializers.CharField(source="vendor.name", read_only=True)
    deliveryAgentId = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    deliveryFee = serializers.IntegerField(source="delivery_fee", read_only=True)
    paymentMethod = serializers.CharField(source="payment_method", read_only=True)
    deliveryType = serializers.CharField(source="delivery_type", read_only=True)
    placedAt = serializers.DateTimeField(source="placed_at", read_only=True)
    deliveryLocation = serializers.CharField(source="delivery_location", read_only=True)
    agentLatitude = serializers.FloatField(source="agent_latitude", read_only=True)
    agentLongitude = serializers.FloatField(source="agent_longitude", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "reference",
            "studentId",
            "studentName",
            "studentPhone",
            "vendorId",
            "vendorName",
            "deliveryAgentId",
            "items",
            "subtotal",
            "deliveryFee",
            "total",
            "paymentMethod",
            "deliveryType",
            "status",
            "placedAt",
            "deliveryLocation",
            "latitude",
            "longitude",
            "agentLatitude",
            "agentLongitude",
        ]

    def get_deliveryAgentId(self, obj):
        return str(obj.delivery_agent_id) if obj.delivery_agent_id else None


class CreateOrderItemSerializer(serializers.Serializer):
    menuItemId = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class CreateOrderSerializer(serializers.Serializer):
    vendorId = serializers.CharField(required=False)
    deliveryType = serializers.ChoiceField(choices=Order.DeliveryType.choices, default="delivery")
    deliveryLocation = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    items = CreateOrderItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An order needs at least one item.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        items_data = validated_data["items"]

        menu_ids = [line["menuItemId"] for line in items_data]
        menu_map = {str(m.id): m for m in MenuItem.objects.filter(id__in=menu_ids)}
        missing = [mid for mid in menu_ids if mid not in menu_map]
        if missing:
            raise serializers.ValidationError({"items": f"Unknown menu items: {missing}"})

        # A cart must come from a single vendor.
        vendor_ids = {menu_map[str(line["menuItemId"])].vendor_id for line in items_data}
        if len(vendor_ids) > 1:
            raise serializers.ValidationError({"items": "All items must be from the same vendor."})

        # Reject items that are currently unavailable.
        unavailable = [
            menu_map[str(line["menuItemId"])].name
            for line in items_data
            if not menu_map[str(line["menuItemId"])].is_available
        ]
        if unavailable:
            raise serializers.ValidationError({"items": f"Currently unavailable: {unavailable}"})

        vendor = menu_map[str(items_data[0]["menuItemId"])].vendor

        delivery_type = validated_data["deliveryType"]
        delivery_fee = DELIVERY_FEE if delivery_type == "delivery" else 0

        order = Order.objects.create(
            student=request.user,
            vendor=vendor,
            delivery_type=delivery_type,
            delivery_fee=delivery_fee,
            delivery_location=validated_data.get("deliveryLocation", "")
            or ("Pickup at vendor counter" if delivery_type == "pickup" else ""),
            latitude=validated_data.get("latitude"),
            longitude=validated_data.get("longitude"),
            status=Order.Status.PLACED,
        )

        for line in items_data:
            item = menu_map[str(line["menuItemId"])]
            OrderItem.objects.create(
                order=order,
                menu_item=item,
                name=item.name,
                unit_price=item.price,
                quantity=line["quantity"],
            )

        order.recalculate_totals()
        order.save(update_fields=["subtotal", "total"])
        return order
