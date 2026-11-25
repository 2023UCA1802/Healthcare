import hashlib

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginIPThrottle(AnonRateThrottle):
    """Limits login attempts per client IP (stops one machine trying many accounts)."""
    scope = "login_ip"


class LoginEmailThrottle(SimpleRateThrottle):
    """Limits login attempts per target email, whatever IP they come from
    (stops a distributed attack on one account). Trade-off: someone can
    briefly lock a victim out of *logging in* by hammering their email."""
    scope = "login_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        ident = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class RegisterThrottle(AnonRateThrottle):
    scope = "register"


class TokenRefreshThrottle(AnonRateThrottle):
    scope = "token_refresh"
