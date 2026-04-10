from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

import jwt
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_sip_password() -> str:
    return secrets.token_urlsafe(18)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def otp_expiry():
    return timezone.now() + timedelta(minutes=settings.OTP_TTL_MINUTES)


def build_access_token(*, user_id: str, role: str, session_id: str) -> str:
    now = timezone.now()
    payload = {
        "sub": str(user_id),
        "role": role,
        "sessionId": str(session_id),
        "iat": int(now.timestamp()),
        "exp": int((now + settings.JWT_ACCESS_TTL).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")


def send_otp_email(email: str, code: str, mode: str) -> None:
    subject = f"Your iTalkVoIP {mode.title()} Verification Code"
    context = {
        "code": code,
        "mode": mode,
        "expires_in_minutes": settings.OTP_TTL_MINUTES,
        "app_name": "iTalkVoIP",
        "support_email": settings.DEFAULT_FROM_EMAIL,
    }
    text_body = render_to_string("core/emails/otp_email.txt", context)
    html_body = render_to_string("core/emails/otp_email.html", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
