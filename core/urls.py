from django.urls import path

from .views import (
    ActiveDomainListView,
    AdminDashboardView,
    AdminDomainDetailView,
    AdminDomainListCreateView,
    AdminLoginView,
    AdminUserListView,
    LogoutView,
    OnboardingDomainView,
    OnboardingExtensionView,
    RefreshView,
    RegisterView,
    ResendLoginOtpView,
    ResendRegistrationOtpView,
    RequestLoginOtpView,
    VerifyLoginOtpView,
    VerifyRegistrationView,
)

urlpatterns = [
    path("auth/register", RegisterView.as_view()),
    path("auth/register/resend-otp", ResendRegistrationOtpView.as_view()),
    path("auth/verify-registration", VerifyRegistrationView.as_view()),
    path("auth/login/request-otp", RequestLoginOtpView.as_view()),
    path("auth/login/resend-otp", ResendLoginOtpView.as_view()),
    path("auth/login/verify-otp", VerifyLoginOtpView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/admin/login", AdminLoginView.as_view()),
    path("domains", ActiveDomainListView.as_view()),
    path("onboarding/domain", OnboardingDomainView.as_view()),
    path("onboarding/extension", OnboardingExtensionView.as_view()),
    path("admin/dashboard", AdminDashboardView.as_view()),
    path("admin/domains", AdminDomainListCreateView.as_view()),
    path("admin/domains/<uuid:domain_id>", AdminDomainDetailView.as_view()),
    path("admin/users", AdminUserListView.as_view()),
]
