from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from notifications.models import Notification

from .models import Order
from .serializers import CreateOrderSerializer, OrderSerializer


def order_summary(order):
    """e.g. '2x Rice and Coconut Beans, 1x Passion Fruit Juice'."""
    return ", ".join(f"{line.quantity}x {line.name}" for line in order.items.all()) or "items"


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

        summary = order_summary(order)
        where = order.delivery_location or "vendor counter"

        Notification.objects.create(
            user=request.user,
            user_role="student",
            title=f"Order received: {summary}",
            body=f"{order.vendor.name} got your order ({summary}) for {where}. {order.total} TZS.",
        )
        Notification.objects.create(
            user_role="vendor",
            title=f"New order from {order.student.full_name}: {summary}",
            body=f"{summary} · {order.get_delivery_type_display()} to {where} · {order.total} TZS. Please confirm.",
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

        summary = order_summary(order)
        where = order.delivery_location or "vendor counter"
        Notification.objects.create(
            user=order.student,
            user_role="student",
            title=f"{summary} — {valid[new_status]}",
            body=f"Your order ({summary}) for {where} is now {valid[new_status]}.",
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

    @action(detail=True, methods=["patch"], url_path="agent-location")
    def agent_location(self, request, pk=None):
        """The delivery agent pushes their live location for map tracking."""
        order = self.get_object()
        if request.user.role != User.Role.DELIVERY:
            return Response({"detail": "Only delivery agents can share location."}, status=403)
        try:
            order.agent_latitude = float(request.data["latitude"])
            order.agent_longitude = float(request.data["longitude"])
        except (KeyError, TypeError, ValueError):
            return Response({"detail": "latitude and longitude are required."}, status=400)
        if not order.delivery_agent_id:
            order.delivery_agent = request.user
        order.save(update_fields=["agent_latitude", "agent_longitude", "delivery_agent", "updated_at"])
        return Response(OrderSerializer(order).data)
