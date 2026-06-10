from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import MenuItem, Vendor


class OrderTests(APITestCase):
    def setUp(self):
        self.v1 = Vendor.objects.create(name="V1")
        self.v2 = Vendor.objects.create(name="V2")
        self.rice = MenuItem.objects.create(vendor=self.v1, name="Rice", price=2500, is_available=True)
        self.juice = MenuItem.objects.create(vendor=self.v1, name="Juice", price=2000, is_available=True)
        self.other = MenuItem.objects.create(vendor=self.v2, name="Burger", price=6000, is_available=True)
        self.closed = MenuItem.objects.create(vendor=self.v1, name="Closed item", price=1000, is_available=False)
        self.student = User.objects.create_user(
            email="st@eatearn.app", password="testpass99", full_name="St", role="student", is_verified=True
        )
        self.vendor_user = User.objects.create_user(
            email="vn@eatearn.app", password="testpass99", full_name="Vn",
            role="vendor", vendor=self.v1, is_verified=True,
        )

    def _place(self, items, delivery_type="delivery", location="Block H"):
        return self.client.post(
            "/api/orders/",
            {"deliveryType": delivery_type, "deliveryLocation": location, "items": items},
            format="json",
        )

    def test_place_order_computes_totals(self):
        self.client.force_authenticate(self.student)
        resp = self._place([
            {"menuItemId": str(self.rice.id), "quantity": 2},
            {"menuItemId": str(self.juice.id), "quantity": 1},
        ])
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["subtotal"], 7000)
        self.assertEqual(resp.data["deliveryFee"], 1000)
        self.assertEqual(resp.data["total"], 8000)
        self.assertEqual(resp.data["status"], "PLACED")

    def test_pickup_has_no_delivery_fee(self):
        self.client.force_authenticate(self.student)
        resp = self._place([{"menuItemId": str(self.rice.id), "quantity": 1}], delivery_type="pickup")
        self.assertEqual(resp.data["deliveryFee"], 0)
        self.assertEqual(resp.data["total"], 2500)

    def test_multi_vendor_cart_rejected(self):
        self.client.force_authenticate(self.student)
        resp = self._place([
            {"menuItemId": str(self.rice.id), "quantity": 1},
            {"menuItemId": str(self.other.id), "quantity": 1},
        ])
        self.assertEqual(resp.status_code, 400)

    def test_unavailable_item_rejected(self):
        self.client.force_authenticate(self.student)
        resp = self._place([{"menuItemId": str(self.closed.id), "quantity": 1}])
        self.assertEqual(resp.status_code, 400)

    def test_order_requires_authentication(self):
        resp = self._place([{"menuItemId": str(self.rice.id), "quantity": 1}])
        self.assertEqual(resp.status_code, 401)

    def test_status_change_respects_role(self):
        self.client.force_authenticate(self.student)
        order = self._place([{"menuItemId": str(self.rice.id), "quantity": 1}]).data
        oid = order["id"]

        # A student may not move an order into PREPARING.
        forbidden = self.client.patch(f"/api/orders/{oid}/status/", {"status": "PREPARING"}, format="json")
        self.assertEqual(forbidden.status_code, 403)

        # The owning vendor can.
        self.client.force_authenticate(self.vendor_user)
        allowed = self.client.patch(f"/api/orders/{oid}/status/", {"status": "CONFIRMED"}, format="json")
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data["status"], "CONFIRMED")

    def test_student_only_sees_own_orders(self):
        self.client.force_authenticate(self.student)
        self._place([{"menuItemId": str(self.rice.id), "quantity": 1}])

        other_student = User.objects.create_user(
            email="st2@eatearn.app", password="testpass99", full_name="St2", role="student", is_verified=True
        )
        self.client.force_authenticate(other_student)
        resp = self.client.get("/api/orders/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)
