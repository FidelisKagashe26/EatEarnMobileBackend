import os
from math import asin, cos, radians, sin, sqrt
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import MenuItem, Vendor
from .serializers import MenuItemSerializer, VendorSerializer


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * r * asin(sqrt(a))


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    http_method_names = ["get", "patch", "head", "options"]

    # A vendor manager may self-update only these fields of their own
    # cafeteria; everything else changes through the admin.
    MANAGER_EDITABLE = {"location", "imageUrl", "isOpen", "etaMinutes"}

    def update(self, request, *args, **kwargs):
        vendor = self.get_object()
        user = request.user
        if getattr(user, "role", None) == "admin" or getattr(user, "is_superuser", False):
            data = request.data
        elif getattr(user, "role", None) == "vendor" and str(user.vendor_id) == str(vendor.pk):
            data = {key: value for key, value in request.data.items() if key in self.MANAGER_EDITABLE}
            if not data:
                raise PermissionDenied("Only the cafeteria location can be changed here — ask an admin for other fields.")
        else:
            raise PermissionDenied("You can only update your own cafeteria.")

        serializer = self.get_serializer(vendor, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def menu(self, request, pk=None):
        items = MenuItem.objects.filter(vendor_id=pk)
        if request.query_params.get("availableOnly") == "true":
            items = items.filter(is_available=True)
        return Response(MenuItemSerializer(items, many=True).data)

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        """Vendors sorted by distance from a ?lat=&lng= point."""
        try:
            lat = float(request.query_params["lat"])
            lng = float(request.query_params["lng"])
        except (KeyError, ValueError):
            return Response({"detail": "lat and lng query params are required."}, status=status.HTTP_400_BAD_REQUEST)

        vendors = list(self.queryset)
        with_distance = []
        for v in vendors:
            if v.latitude is None or v.longitude is None:
                continue
            v_distance = round(haversine_km(lat, lng, v.latitude, v.longitude), 2)
            data = VendorSerializer(v).data
            data["distanceKm"] = v_distance
            with_distance.append((v_distance, data))
        with_distance.sort(key=lambda pair: pair[0])
        return Response([data for _, data in with_distance])


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related("vendor").all()
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        vendor_id = self.request.query_params.get("vendorId")
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)
        if self.request.query_params.get("availableOnly") == "true":
            qs = qs.filter(is_available=True)
        return qs

    def _assert_can_edit(self, vendor_id):
        """Only the vendor that owns the menu (or an admin) may write to it."""
        user = self.request.user
        if getattr(user, "role", None) == "admin" or getattr(user, "is_superuser", False):
            return
        if getattr(user, "role", None) == "vendor" and str(user.vendor_id) == str(vendor_id):
            return
        raise PermissionDenied("You can only manage your own cafeteria's menu.")

    def perform_create(self, serializer):
        self._assert_can_edit(serializer.validated_data["vendor_id"])
        serializer.save()

    def perform_update(self, serializer):
        self._assert_can_edit(serializer.instance.vendor_id)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_can_edit(instance.vendor_id)
        instance.delete()

    @action(detail=True, methods=["patch"])
    def toggle(self, request, pk=None):
        item = self.get_object()
        self._assert_can_edit(item.vendor_id)
        item.is_available = not item.is_available
        item.save(update_fields=["is_available"])
        return Response(self.get_serializer(item).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request):
        """Vendors upload a food photo; returns the public URL to store on the item."""
        if getattr(request.user, "role", None) not in ("vendor", "admin") and not request.user.is_superuser:
            raise PermissionDenied("Only vendors can upload food photos.")

        file = request.FILES.get("image")
        if not file:
            return Response({"detail": "Attach the photo in an 'image' field."}, status=status.HTTP_400_BAD_REQUEST)
        if file.size > 5 * 1024 * 1024:
            return Response({"detail": "The image must be smaller than 5MB."}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name or "")[1].lower() or ".jpg"
        stored = default_storage.save(f"menu/{uuid4().hex}{ext}", file)
        media_url = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else f"/{settings.MEDIA_URL}"
        return Response(
            {"url": request.build_absolute_uri(f"{media_url}{stored}")},
            status=status.HTTP_201_CREATED,
        )
