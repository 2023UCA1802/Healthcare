from .models import AuditLog
from .utils import log_event

_ACTIONS = {
    "POST": AuditLog.Action.CREATE,
    "PUT": AuditLog.Action.UPDATE,
    "PATCH": AuditLog.Action.UPDATE,
    "DELETE": AuditLog.Action.DELETE,
}


class AuditedMixin:
    """Add to a DRF view to record every authenticated request against it
    (including denied/not-found ones, with the status code)."""

    audit_resource = ""

    def get_audit_target(self, request, response):
        """Return (resource_type, resource_id). Override for unusual routes."""
        rid = self.kwargs.get("pk")
        if rid is None and request.method == "POST" and isinstance(getattr(response, "data", None), dict):
            rid = response.data.get("id")
        return self.audit_resource, rid

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            try:
                user = request.user
            except Exception:  # authentication blew up before we got here
                return response
            if getattr(user, "is_authenticated", False):
                if request.method == "GET":
                    action = AuditLog.Action.VIEW if self.kwargs.get("pk") is not None else AuditLog.Action.LIST
                else:
                    action = _ACTIONS[request.method]
                resource_type, resource_id = self.get_audit_target(request, response)
                log_event(
                    request, action, user=user, resource_type=resource_type,
                    resource_id=resource_id, status_code=response.status_code,
                )
        return response
