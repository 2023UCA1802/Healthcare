import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import AuditLog
from audit.utils import log_event
from core.security import enforce_trusted_origin
from core.throttles import LoginEmailThrottle, LoginIPThrottle, RegisterThrottle, TokenRefreshThrottle

from .cookies import clear_refresh_cookie, set_refresh_cookie
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


def _session_response(user):
    """New access token in the body; new refresh token ONLY in an HttpOnly cookie."""
    refresh = RefreshToken.for_user(user)
    response = Response(
        {"user": UserSerializer(user).data, "access": str(refresh.access_token)},
        status=status.HTTP_200_OK,
    )
    set_refresh_cookie(response, str(refresh))
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RegisterThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Same response whether or not the email is already registered, so the
        # endpoint can't be used to find out who has an account.
        try:
            with transaction.atomic():
                if not User.objects.filter(email__iexact=data["email"]).exists():
                    user = User.objects.create_user(
                        email=data["email"], name=data["name"], password=data["password"]
                    )
                    log_event(request, AuditLog.Action.REGISTER, user=user, status_code=201)
        except IntegrityError:
            pass  # lost a race with a concurrent registration of the same email

        return Response(
            {"message": "If this email can be registered, the account has been created. Please log in."},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            attempted = request.data.get("email", "") if hasattr(request.data, "get") else ""
            log_event(
                request, AuditLog.Action.LOGIN_FAILED,
                email=attempted if isinstance(attempted, str) else "", status_code=400,
            )
            serializer.is_valid(raise_exception=True)  # re-raises -> 400
        user = serializer.validated_data["user"]
        log_event(request, AuditLog.Action.LOGIN_SUCCESS, user=user, status_code=200)
        return _session_response(user)


class RefreshView(APIView):
    """Exchange the refresh cookie for a new access token (and rotate the cookie).

    The old refresh token is blacklisted on use; presenting it again fails.
    Also used on page load to restore the session, hence it returns the user.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [TokenRefreshThrottle]

    def post(self, request):
        enforce_trusted_origin(request)
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        user = None
        if raw:
            try:
                old = RefreshToken(raw)  # verifies signature, expiry and blacklist
                user = User.objects.filter(pk=old["user_id"], is_active=True).first()
                if user:
                    old.blacklist()
            except (TokenError, KeyError):
                user = None
        if user is None:
            response = Response({"detail": "Session expired. Please log in again."}, status=401)
            clear_refresh_cookie(response)
            return response
        return _session_response(user)


class LogoutView(APIView):
    """Blacklists the refresh token server-side and clears the cookie."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [TokenRefreshThrottle]

    def post(self, request):
        enforce_trusted_origin(request)
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                token = RefreshToken(raw)
                user = User.objects.filter(pk=token["user_id"]).first()
                token.blacklist()
                if user:
                    log_event(request, AuditLog.Action.LOGOUT, user=user, status_code=204)
            except (TokenError, KeyError):
                pass  # already invalid: nothing to revoke
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response
