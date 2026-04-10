from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from .models import Domain, EmailOTP, Extension, OtpPurpose, Session, User, UserRole
from .utils import (
    build_access_token,
    generate_otp_code,
    generate_refresh_token,
    generate_sip_password,
    hash_token,
    otp_expiry,
    send_otp_email,
)


class Conflict(APIException):
    status_code = 409
    default_detail = "Conflict"


def issue_otp(*, user: User, purpose: str) -> None:
    code = generate_otp_code()
    EmailOTP.objects.create(
        user=user,
        purpose=purpose,
        code=code,
        expires_at=otp_expiry(),
    )
    mode = "registration" if purpose == OtpPurpose.REGISTRATION else "login"
    send_otp_email(user.email, code, mode)


def consume_otp(*, email: str, code: str, purpose: str) -> User:
    try:
        user = User.objects.get(email=email.lower())
    except User.DoesNotExist as exc:
        raise NotFound("User not found") from exc

    otp = (
        EmailOTP.objects.filter(
            user=user,
            purpose=purpose,
            code=code,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise ValidationError({"detail": "Invalid or expired OTP"})

    otp.consumed_at = timezone.now()
    otp.save(update_fields=["consumed_at"])
    return user


def create_session(*, user: User, user_agent: str = "", ip_address: str | None = None) -> dict:
    refresh_token = generate_refresh_token()
    session = Session.objects.create(
        user=user,
        refresh_token_hash=hash_token(refresh_token),
        user_agent=(user_agent or "")[:255],
        ip_address=ip_address,
        expires_at=timezone.now() + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS),
    )
    return {
        "accessToken": build_access_token(user_id=str(user.id), role=user.role, session_id=str(session.id)),
        "refreshToken": refresh_token,
        "session": {
            "id": str(session.id),
            "expiresAt": session.expires_at.isoformat(),
        },
    }


def rotate_session(*, refresh_token: str, user_agent: str = "", ip_address: str | None = None) -> dict | None:
    session = (
        Session.objects.select_related("user")
        .filter(
            refresh_token_hash=hash_token(refresh_token),
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .first()
    )
    if session is None:
        return None

    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
    return create_session(user=session.user, user_agent=user_agent, ip_address=ip_address)


def revoke_session(*, refresh_token: str) -> None:
    Session.objects.filter(refresh_token_hash=hash_token(refresh_token), revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def register_user(*, email: str) -> dict:
    email = email.lower()
    user = User.objects.filter(email=email).first()
    if user and user.role != UserRole.USER:
        raise Conflict("This email belongs to an admin account")
    if user is None:
        user = User.objects.create_user(email=email, role=UserRole.USER)

    issue_otp(user=user, purpose=OtpPurpose.REGISTRATION)
    return {
        "message": "OTP sent to email",
        "email": user.email,
        "expiresInMinutes": settings.OTP_TTL_MINUTES,
    }


def resend_registration_otp(*, email: str) -> dict:
    email = email.lower()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise NotFound("User not found") from exc

    if user.role != UserRole.USER:
        raise Conflict("This email belongs to an admin account")
    if user.is_verified:
        raise ValidationError({"detail": "Email is already verified"})

    issue_otp(user=user, purpose=OtpPurpose.REGISTRATION)
    return {
        "message": "Registration OTP resent",
        "email": user.email,
        "expiresInMinutes": settings.OTP_TTL_MINUTES,
    }


def verify_registration_otp(*, email: str, otp: str, user_agent: str = "", ip_address: str | None = None) -> dict:
    user = consume_otp(email=email, code=otp, purpose=OtpPurpose.REGISTRATION)
    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
    tokens = create_session(user=user, user_agent=user_agent, ip_address=ip_address)
    return {
        "message": "Email verified successfully",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "isVerified": user.is_verified,
        },
        "tokens": tokens,
    }


def request_login_otp(*, email: str) -> dict:
    email = email.lower()
    try:
        user = User.objects.get(email=email, role=UserRole.USER)
    except User.DoesNotExist as exc:
        raise NotFound("User not found") from exc

    if not user.is_verified:
        raise PermissionDenied("Email must be verified before login")

    issue_otp(user=user, purpose=OtpPurpose.LOGIN)
    return {
        "message": "Login OTP sent to email",
        "email": user.email,
        "expiresInMinutes": settings.OTP_TTL_MINUTES,
    }


def resend_login_otp(*, email: str) -> dict:
    email = email.lower()
    try:
        user = User.objects.get(email=email, role=UserRole.USER)
    except User.DoesNotExist as exc:
        raise NotFound("User not found") from exc

    if not user.is_verified:
        raise PermissionDenied("Email must be verified before login")

    issue_otp(user=user, purpose=OtpPurpose.LOGIN)
    return {
        "message": "Login OTP resent",
        "email": user.email,
        "expiresInMinutes": settings.OTP_TTL_MINUTES,
    }


def verify_login_otp(*, email: str, otp: str, user_agent: str = "", ip_address: str | None = None) -> dict:
    user = consume_otp(email=email, code=otp, purpose=OtpPurpose.LOGIN)
    if not user.is_verified:
        raise PermissionDenied("Email must be verified before login")

    tokens = create_session(user=user, user_agent=user_agent, ip_address=ip_address)
    return {
        "message": "Login successful",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "isVerified": user.is_verified,
        },
        "tokens": tokens,
    }


def authenticate_admin(*, email: str, password: str) -> User | None:
    user = authenticate(email=email.lower(), password=password)
    if user is None or user.role != UserRole.ADMIN:
        return None
    return user


def admin_dashboard() -> dict:
    return {
        "stats": {
            "users": User.objects.filter(role=UserRole.USER).count(),
            "domains": Domain.objects.count(),
            "provisionedExtensions": Extension.objects.count(),
        }
    }


def list_admin_domains() -> dict:
    domains = Domain.objects.annotate(
        users_count=Count("selected_by_users"),
        extensions_count=Count("extensions"),
    ).order_by("-created_at")
    return {
        "data": [
            {
                "id": str(domain.id),
                "identifier": domain.identifier,
                "label": domain.label,
                "isActive": domain.is_active,
                "extensionStart": domain.extension_start,
                "createdAt": domain.created_at.isoformat(),
                "updatedAt": domain.updated_at.isoformat(),
                "usage": {
                    "users": domain.users_count,
                    "extensions": domain.extensions_count,
                },
            }
            for domain in domains
        ]
    }


def list_admin_users() -> dict:
    users = User.objects.filter(role=UserRole.USER).select_related("selected_domain").prefetch_related("extension")
    data = []
    for user in users:
        extension = getattr(user, "extension", None)
        data.append(
            {
                "id": str(user.id),
                "email": user.email,
                "isVerified": user.is_verified,
                "createdAt": user.created_at.isoformat(),
                "selectedDomain": (
                    {
                        "id": str(user.selected_domain.id),
                        "identifier": user.selected_domain.identifier,
                        "label": user.selected_domain.label,
                    }
                    if user.selected_domain
                    else None
                ),
                "extension": (
                    {
                        "number": extension.extension_number,
                        "password": extension.sip_password,
                    }
                    if extension
                    else None
                ),
            }
        )
    return {"data": data}


def create_domain(*, identifier: str, label: str, extension_start: int = 1000) -> dict:
    domain = Domain.objects.create(
        identifier=identifier,
        label=label,
        extension_start=extension_start,
    )
    return serialize_domain_result("Domain created successfully", domain)


def update_domain(*, domain: Domain, **changes) -> dict:
    for key, value in changes.items():
        setattr(domain, key, value)
    domain.save()
    return serialize_domain_result("Domain updated successfully", domain)


def serialize_domain_result(message: str, domain: Domain) -> dict:
    return {
        "message": message,
        "data": {
            "id": str(domain.id),
            "identifier": domain.identifier,
            "label": domain.label,
            "isActive": domain.is_active,
            "extensionStart": domain.extension_start,
            "createdAt": domain.created_at.isoformat(),
            "updatedAt": domain.updated_at.isoformat(),
        },
    }


def list_active_domains() -> dict:
    domains = Domain.objects.filter(is_active=True).order_by("label")
    return {
        "data": [
            {
                "id": str(domain.id),
                "identifier": domain.identifier,
                "label": domain.label,
            }
            for domain in domains
        ]
    }


def get_next_extension_number(*, domain: Domain) -> int:
    candidate = domain.extension_start
    existing_numbers = list(domain.extensions.order_by("extension_number").values_list("extension_number", flat=True))
    for number in existing_numbers:
        if number == candidate:
            candidate += 1
            continue
        if number > candidate:
            break
    return candidate


def assign_domain_and_provision_extension(*, user: User, domain_id: str) -> dict:
    try:
        domain = Domain.objects.get(id=domain_id, is_active=True)
    except Domain.DoesNotExist as exc:
        raise NotFound("Domain not found") from exc

    existing_extension = getattr(user, "extension", None)
    if existing_extension:
        return {
            "domain": {
                "id": str(existing_extension.domain.id),
                "identifier": existing_extension.domain.identifier,
                "label": existing_extension.domain.label,
            },
            "extension": {
                "number": existing_extension.extension_number,
                "password": existing_extension.sip_password,
            },
            "alreadyProvisioned": True,
        }

    for _ in range(3):
        try:
            with transaction.atomic():
                locked_domain = Domain.objects.select_for_update().get(id=domain.id)
                extension = Extension.objects.create(
                    user=user,
                    domain=locked_domain,
                    extension_number=get_next_extension_number(domain=locked_domain),
                    sip_password=generate_sip_password(),
                )
                user.selected_domain = locked_domain
                user.save(update_fields=["selected_domain"])
            return {
                "domain": {
                    "id": str(extension.domain.id),
                    "identifier": extension.domain.identifier,
                    "label": extension.domain.label,
                },
                "extension": {
                    "number": extension.extension_number,
                    "password": extension.sip_password,
                },
                "alreadyProvisioned": False,
            }
        except IntegrityError:
            continue

    raise Conflict("Unable to allocate extension")


def get_extension_details(*, user: User) -> dict:
    extension = getattr(user, "extension", None)
    if extension is None:
        raise NotFound("Extension not assigned yet")
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
        },
        "domain": {
            "id": str(extension.domain.id),
            "identifier": extension.domain.identifier,
            "label": extension.domain.label,
        },
        "extension": {
            "number": extension.extension_number,
            "password": extension.sip_password,
        },
    }
