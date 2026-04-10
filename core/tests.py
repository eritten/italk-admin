from datetime import timedelta

from django.core import mail
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .admin import ExtensionAdmin
from .models import Domain, EmailOTP, Extension, User, UserRole


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.domain = Domain.objects.create(identifier="us-east", label="US East")

    def test_register_and_verify_registration(self):
        free_extension = Extension.objects.create(
            domain=self.domain,
            extension_number=1000,
            sip_password="sip-pass-1000",
        )
        response = self.client.post(
            "/api/v1/auth/register",
            {"email": "user@example.com", "domainId": str(self.domain.id)},
            format="json",
        )
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
        self.assertEqual(verify.json()["assignment"]["extension"]["number"], 1000)
        free_extension.refresh_from_db()
        self.assertEqual(free_extension.user.email, "user@example.com")

    def test_verify_registration_returns_existing_extension_for_user(self):
        user = User.objects.create_user(
            email="user@example.com",
            role=UserRole.USER,
            is_verified=False,
            selected_domain=self.domain,
        )
        Extension.objects.create(
            user=user,
            domain=self.domain,
            extension_number=1000,
            sip_password="sip-pass-1000",
        )
        EmailOTP.objects.create(
            user=user,
            purpose="REGISTRATION",
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        verify = self.client.post(
            "/api/v1/auth/verify-registration",
            {"email": "user@example.com", "otp": "123456"},
            format="json",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.json()["assignment"]["alreadyProvisioned"])
        self.assertEqual(verify.json()["assignment"]["extension"]["number"], 1000)

    def test_register_with_domain_uuid_alias_is_supported(self):
        response = self.client.post(
            "/api/v1/auth/register",
            {"email": "alias@example.com", "domainUuid": str(self.domain.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(email="alias@example.com").selected_domain, self.domain)

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

    def test_onboarding_domain_assigns_first_free_extension(self):
        Extension.objects.create(domain=self.domain, extension_number=1001, sip_password="sip-pass-1001")
        Extension.objects.create(domain=self.domain, extension_number=1000, sip_password="sip-pass-1000")
        user = User.objects.create_user(
            email="user2@example.com",
            role=UserRole.USER,
            is_verified=True,
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/v1/onboarding/domain",
            {"domainId": str(self.domain.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["extension"]["number"], 1000)


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

    def test_extension_admin_hides_user_field_when_creating(self):
        admin_view = ExtensionAdmin(Extension, AdminSite())
        create_fields = admin_view.get_fields(request=None, obj=None)
        change_fields = admin_view.get_fields(request=None, obj=Extension(domain=Domain.objects.first(), extension_number=1000))

        self.assertNotIn("user", create_fields)
        self.assertIn("user", change_fields)
