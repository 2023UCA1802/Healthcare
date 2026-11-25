import logging

from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .utils import get_client_ip

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Consistent error shape; DB constraint problems become 409 instead of 500."""
    response = exception_handler(exc, context)

    if response is None and isinstance(exc, IntegrityError):
        return Response(
            {"detail": "A database constraint was violated (duplicate or invalid reference)."},
            status=status.HTTP_409_CONFLICT,
        )
    if response is None and isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This record is still referenced by other records. Remove those first."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, Throttled):
        request = context.get("request")
        logger.warning(
            "Rate limit hit: %s %s from %s",
            getattr(request, "method", "?"),
            getattr(request, "path", "?"),
            get_client_ip(request) if request is not None else "?",
        )
    return response
