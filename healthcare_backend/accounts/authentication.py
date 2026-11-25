from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from .models import RevokedSession


class SessionAwareJWTAuthentication(JWTAuthentication):
    """Standard JWT check, plus: reject access tokens whose session was logged out."""

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)  # signature, expiry, type
        sid = token.get("sid")
        if not sid:
            raise InvalidToken("Token has no session. Please log in again.")
        if RevokedSession.objects.filter(sid=sid).exists():
            raise InvalidToken("Token has been revoked. Please log in again.")
        return token