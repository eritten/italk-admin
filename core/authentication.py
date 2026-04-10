from __future__ import annotations

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from .models import Session, User


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        try:
            payload = jwt.decode(parts[1], settings.JWT_ACCESS_SECRET, algorithms=["HS256"])
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed("Invalid access token") from exc

        user_id = payload.get("sub")
        session_id = payload.get("sessionId")
        if not user_id:
            raise exceptions.AuthenticationFailed("Invalid access token")

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("User not found") from exc

        if session_id and not Session.objects.filter(
            id=session_id,
            user=user,
            revoked_at__isnull=True,
        ).exists():
            raise exceptions.AuthenticationFailed("Session revoked")

        request.auth_payload = payload
        return user, payload
