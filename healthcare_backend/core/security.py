from urllib.parse import urlsplit

from django.conf import settings
from rest_framework.exceptions import PermissionDenied


def enforce_trusted_origin(request):
    """Defence in depth for endpoints that authenticate with a cookie.

    SameSite already stops cross-site cookie sends; this additionally rejects
    requests whose Origin (or Referer) is not one of our own frontends.
    Requests carrying neither header (curl, server-to-server) are allowed,
    since a browser always sends Origin on cross-origin POSTs.
    """
    origin = request.headers.get("Origin")
    if not origin:
        referer = request.headers.get("Referer")
        if referer:
            parts = urlsplit(referer)
            origin = f"{parts.scheme}://{parts.netloc}"
    if origin and origin not in settings.TRUSTED_ORIGINS:
        raise PermissionDenied("Origin not allowed.")
