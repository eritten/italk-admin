from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Domain
from .permissions import IsAdminRole, IsUserRole
from .serializers import (
    AdminDomainCreateSerializer,
    AdminDomainUpdateSerializer,
    AdminLoginSerializer,
    DomainSelectSerializer,
    EmailSerializer,
    RefreshSerializer,
    VerifyOtpSerializer,
)
from .services import (
    admin_dashboard,
    assign_domain_and_provision_extension,
    authenticate_admin,
    create_domain,
    create_session,
    get_extension_details,
    list_active_domains,
    list_admin_domains,
    list_admin_users,
    register_user,
    resend_login_otp,
    resend_registration_otp,
    request_login_otp,
    revoke_session,
    rotate_session,
    update_domain,
    verify_login_otp,
    verify_registration_otp,
)


def request_meta(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
    return {
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "ip_address": ip_address,
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(register_user(email=serializer.validated_data["email"]))


class VerifyRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            verify_registration_otp(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
                **request_meta(request),
            )
        )


class ResendRegistrationOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(resend_registration_otp(email=serializer.validated_data["email"]))


class RequestLoginOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(request_login_otp(email=serializer.validated_data["email"]))


class ResendLoginOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(resend_login_otp(email=serializer.validated_data["email"]))


class VerifyLoginOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            verify_login_otp(
                email=serializer.validated_data["email"],
                otp=serializer.validated_data["otp"],
                **request_meta(request),
            )
        )


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = rotate_session(
            refresh_token=serializer.validated_data["refreshToken"],
            **request_meta(request),
        )
        if tokens is None:
            return Response({"detail": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"message": "Session refreshed", "tokens": tokens})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revoke_session(refresh_token=serializer.validated_data["refreshToken"])
        return Response({"message": "Logged out successfully"})


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_admin(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid admin credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        tokens = create_session(user=user, **request_meta(request))
        return Response(
            {
                "message": "Admin login successful",
                "admin": {
                    "id": str(user.id),
                    "email": user.email,
                },
                "tokens": tokens,
            }
        )


class ActiveDomainListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(list_active_domains())


class OnboardingDomainView(APIView):
    permission_classes = [IsUserRole]

    def post(self, request):
        serializer = DomainSelectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            assign_domain_and_provision_extension(
                user=request.user,
                domain_id=str(serializer.validated_data["domainId"]),
            )
        )


class OnboardingExtensionView(APIView):
    permission_classes = [IsUserRole]

    def get(self, request):
        return Response(get_extension_details(user=request.user))


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(admin_dashboard())


class AdminDomainListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(list_admin_domains())

    def post(self, request):
        serializer = AdminDomainCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(
            create_domain(
                identifier=data["identifier"],
                label=data["label"],
                extension_start=data.get("extensionStart", 1000),
            ),
            status=status.HTTP_201_CREATED,
        )


class AdminDomainDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, domain_id):
        serializer = AdminDomainUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        domain = get_object_or_404(Domain, id=domain_id)
        mapping = {"label": "label", "isActive": "is_active", "extensionStart": "extension_start"}
        updates = {
            model_key: serializer.validated_data[incoming_key]
            for incoming_key, model_key in mapping.items()
            if incoming_key in serializer.validated_data
        }
        return Response(update_domain(domain=domain, **updates))


class AdminUserListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(list_admin_users())
