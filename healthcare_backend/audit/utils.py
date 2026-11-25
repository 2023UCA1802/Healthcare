import logging

from core.utils import get_client_ip

from .models import AuditLog

logger = logging.getLogger("audit")


def log_event(request, action, *, user=None, email="", resource_type="", resource_id=None, status_code=None):
    user = user if (user is not None and getattr(user, "is_authenticated", False)) else None
    email = (user.email if user else email) or ""
    ip = get_client_ip(request)
    entry = AuditLog.objects.create(
        user=user,
        user_email=email[:254],
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status_code=status_code,
        ip_address=ip,
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
    )
    logger.info(
        "user=%s action=%s resource=%s#%s status=%s ip=%s",
        email or "-", action, resource_type or "-", resource_id, status_code, ip,
    )
    return entry
