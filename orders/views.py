from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from notifications.models import Notification

from .models import Order
from .serializers import CreateOrderSerializer, OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = Order.objects.select_related("vendor", "student", "delivery_agent").prefetch_related("items")

        if user.role == User.Role.STUDENT:
            return base.filter(student=user)
        if user.role == User.Role.VENDOR:
            return base.filter(vendor=user.vendor) if user.vendor_id else base.none()
        if user.role == User.Role.DELIVERY:
            # Orders assigned to me, plus delivery orders ready for pickup.
            return base.filter(
                Q(delivery_agent=user)
                | Q(delivery_type="delivery", status__in=["READY", "OUT_FOR_DELIVERY"])
            )
        return base  # admin sees everything

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        Notification.objects.create(
            user=request.user,
            user_role="student",
            title=f"Order #{order.id} received",
            body="The vendor has received your order. You will get updates shortly.",
        )
        Notification.objects.create(
            user_role="vendor",
            title=f"New order #{order.id}",
            body=f"{order.items.count()} item(s) for {order.total} TZS. Please confirm.",
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    # Which statuses each role is allowed to set.
    ALLOWED_STATUS_BY_ROLE = {
        "admin": set(dict(Order.Status.choices).keys()),
        "vendor": {"CONFIRMED", "PREPARING", "READY", "CANCELLED"},
        "delivery": {"OUT_FOR_DELIVERY", "DELIVERED"},
        "student": {"CANCELLED"},
    }

    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        valid = dict(Order.Status.choices)
        if new_status not in valid:
            return Response({"detail": "Invalid status."}, status=400)

        allowed = self.ALLOWED_STATUS_BY_ROLE.get(request.user.role, set())
        if new_status not in allowed:
            return Response(
                {"detail": f"A {request.user.role} cannot set status '{new_status}'."},
                status=403,
            )

        order.status = new_status
        # When a delivery order goes out, assign the acting delivery agent.
        if new_status == "OUT_FOR_DELIVERY" and request.user.role == "delivery" and not order.delivery_agent_id:
            order.delivery_agent = request.user
        order.save()

        Notification.objects.create(
            user=order.student,
            user_role="student",
            title=f"Order #{order.id} is now {valid[new_status]}",
            body=f"Your order status changed to {valid[new_status]}.",
        )
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["patch"])
    def accept(self, request, pk=None):
        """A delivery agent claims an available delivery order."""
        order = self.get_object()
        order.delivery_agent = request.user
        if order.status == "READY":
            order.status = "OUT_FOR_DELIVERY"
        order.save()
        return Response(OrderSerializer(order).data)
