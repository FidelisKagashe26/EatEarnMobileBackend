from math import asin, cos, radians, sin, sqrt

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import MenuItem, Vendor
from .serializers import MenuItemSerializer, VendorSerializer


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * r * asin(sqrt(a))


class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer

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

    @action(detail=True, methods=["patch"])
    def toggle(self, request, pk=None):
        item = self.get_object()
        item.is_available = not item.is_available
        item.save(update_fields=["is_available"])
        return Response(self.get_serializer(item).data)
