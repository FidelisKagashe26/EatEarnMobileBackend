from rest_framework.test import APITestCase

from accounts.models import User

from .models import MenuItem, Vendor


class CatalogTests(APITestCase):
    def setUp(self):
        self.v1 = Vendor.objects.create(name="V1", location="Block A", latitude=-6.26, longitude=35.95)
        self.v2 = Vendor.objects.create(name="V2", location="Block B", latitude=-6.27, longitude=35.96)
        MenuItem.objects.create(vendor=self.v1, name="Rice", price=2000, category="Lunch", is_available=True)
        self.owner = User.objects.create_user(
            email="v1@eatearn.app", password="testpass99", full_name="V1 mgr",
            role="vendor", vendor=self.v1, is_verified=True,
        )
        self.other = User.objects.create_user(
            email="v2@eatearn.app", password="testpass99", full_name="V2 mgr",
            role="vendor", vendor=self.v2, is_verified=True,
        )

    def test_vendor_list_is_public(self):
        resp = self.client.get("/api/vendors/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_nearby_is_sorted_with_distance(self):
        resp = self.client.get("/api/vendors/nearby/?lat=-6.26&lng=35.95")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]["name"], "V1")
        self.assertIn("distanceKm", resp.data[0])

    def test_owner_can_add_menu_item(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.post(
            "/api/menu-items/",
            {"vendorId": str(self.v1.id), "name": "Beans", "price": 1500, "category": "Lunch", "isAvailable": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_vendor_cannot_edit_other_menu(self):
        self.client.force_authenticate(self.other)
        resp = self.client.post(
            "/api/menu-items/",
            {"vendorId": str(self.v1.id), "name": "X", "price": 1000, "category": "Lunch", "isAvailable": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_toggle_requires_ownership(self):
        item = MenuItem.objects.create(vendor=self.v1, name="Tea", price=500, is_available=True)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.patch(f"/api/menu-items/{item.id}/toggle/").status_code, 403)

        self.client.force_authenticate(self.owner)
        resp = self.client.patch(f"/api/menu-items/{item.id}/toggle/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["isAvailable"])
