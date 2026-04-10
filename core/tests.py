from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Domain, EmailOTP, User, UserRole


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_verify_registration(self):
        response = self.client.post("/api/v1/auth/register", {"email": "user@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("multipart/alternative", mail.outbox[0].message().get_content_type())
        self.assertIn("Your verification code", mail.outbox[0].alternatives[0].content)

        otp = EmailOTP.objects.get(user__email="user@example.com", purpose="REGISTRATION")
        verify = self.client.post(
            "/api/v1/auth/verify-registration",
            {"email": "user@example.com", "otp": otp.code},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertIn("accessToken", verify.json()["tokens"])

    def test_resend_registration_otp_creates_new_code(self):
        self.client.post("/api/v1/auth/register", {"email": "user@example.com"}, format="json")
        response = self.client.post(
            "/api/v1/auth/register/resend-otp",
            {"email": "user@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EmailOTP.objects.filter(user__email="user@example.com", purpose="REGISTRATION").count(),
            2,
        )

    def test_resend_login_otp_creates_new_code(self):
        user = User.objects.create_user(
            email="verified@example.com",
            role=UserRole.USER,
            is_verified=True,
        )
        response = self.client.post(
            "/api/v1/auth/login/resend-otp",
            {"email": user.email},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EmailOTP.objects.filter(user=user, purpose="LOGIN").count(),
            1,
        )


class AdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="ChangeMe123!",
            role=UserRole.ADMIN,
            is_verified=True,
            is_staff=True,
        )
        Domain.objects.create(identifier="us-east", label="US East")

    def test_admin_can_log_in_and_fetch_dashboard(self):
        login = self.client.post(
            "/api/v1/auth/admin/login",
            {"email": "admin@example.com", "password": "ChangeMe123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["tokens"]["accessToken"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        dashboard = self.client.get("/api/v1/admin/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("stats", dashboard.json())
