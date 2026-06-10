from rest_framework.test import APITestCase

from .models import User


class AuthFlowTests(APITestCase):
    def test_register_verify_login_flow(self):
        resp = self.client.post(
            "/api/auth/register/",
            {
                "fullName": "Test User",
                "email": "new@eatearn.app",
                "phone": "+255700000001",
                "role": "student",
                "password": "testpass99",
                "studentId": "2024-1",
                "hostelBlock": "Block B",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("devOtp", resp.data)

        user = User.objects.get(email="new@eatearn.app")
        self.assertFalse(user.is_verified)

        verify = self.client.post(
            "/api/auth/verify-otp/",
            {"email": "new@eatearn.app", "code": resp.data["devOtp"]},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertIn("tokens", verify.data)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

        login = self.client.post(
            "/api/auth/login/",
            {"email": "new@eatearn.app", "password": "testpass99"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["user"]["role"], "student")

    def test_login_does_not_take_a_role(self):
        # The role comes from the account, never from the request.
        User.objects.create_user(
            email="vend@eatearn.app", password="testpass99", full_name="V", role="vendor", is_verified=True
        )
        resp = self.client.post(
            "/api/auth/login/",
            {"email": "vend@eatearn.app", "password": "testpass99", "role": "admin"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["user"]["role"], "vendor")

    def test_wrong_password_rejected(self):
        User.objects.create_user(
            email="a@eatearn.app", password="rightpass1", full_name="A", role="student"
        )
        resp = self.client.post(
            "/api/auth/login/", {"email": "a@eatearn.app", "password": "nope"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_bad_otp_rejected(self):
        self.client.post(
            "/api/auth/register/",
            {"fullName": "B", "email": "b@eatearn.app", "phone": "+255", "role": "student", "password": "testpass99"},
            format="json",
        )
        resp = self.client.post(
            "/api/auth/verify-otp/", {"email": "b@eatearn.app", "code": "000000"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dup@eatearn.app", password="testpass99", full_name="D", role="student")
        resp = self.client.post(
            "/api/auth/register/",
            {"fullName": "D2", "email": "dup@eatearn.app", "phone": "+255", "role": "student", "password": "testpass99"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_users_list_is_admin_only(self):
        student = User.objects.create_user(
            email="s@eatearn.app", password="testpass99", full_name="S", role="student", is_verified=True
        )
        self.client.force_authenticate(student)
        self.assertEqual(self.client.get("/api/auth/users/").status_code, 403)

        admin = User.objects.create_superuser(
            email="ad@eatearn.app", password="testpass99", full_name="Ad"
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get("/api/auth/users/").status_code, 200)
