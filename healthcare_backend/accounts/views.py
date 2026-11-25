import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from audit.models import AuditLog
from audit.utils import log_event
from core.security import enforce_trusted_origin
from core.throttles import LoginEmailThrottle, LoginIPThrottle, RegisterThrottle, TokenRefreshThrottle

from .cookies import clear_refresh_cookie, set_refresh_cookie
from .models import RevokedSession
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


def _session_response(user, sid=None):
    """New access token in the body; new refresh token ONLY in an HttpOnly cookie.

    `sid` identifies the login session. It is copied into both tokens (and kept
    across refreshes) so that logging out can revoke the session's access tokens.
    """
    refresh = RefreshToken.for_user(user)
    refresh["sid"] = sid or uuid.uuid4().hex
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
        sid = None
        if raw:
            try:
                old = RefreshToken(raw)  # verifies signature, expiry and blacklist
                sid = old.get("sid")
                user = User.objects.filter(pk=old["user_id"], is_active=True).first()
                if user and sid and not RevokedSession.objects.filter(sid=sid).exists():
                    old.blacklist()
                else:
                    user = None
            except (TokenError, KeyError):
                user = None
        if user is None:
            response = Response({"detail": "Session expired. Please log in again."}, status=401)
            clear_refresh_cookie(response)
            return response
        return _session_response(user, sid=sid)  # same session id across rotations


class LogoutView(APIView):
    """Ends the session: blacklists the refresh token, revokes the session's
    access tokens immediately, and clears the cookie.

    The session is identified from the refresh cookie and/or an
    `Authorization: Bearer <access>` header, so it also works for API clients
    (e.g. Postman) that only hold an access token.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [TokenRefreshThrottle]

    def post(self, request):
        enforce_trusted_origin(request)
        sids, user = set(), None

        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                token = RefreshToken(raw)
                user = User.objects.filter(pk=token["user_id"]).first()
                if token.get("sid"):
                    sids.add(token["sid"])
                token.blacklist()
            except (TokenError, KeyError):
                pass  # already invalid: nothing to revoke

        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            try:
                access = AccessToken(header[7:].strip())
                if access.get("sid"):
                    sids.add(access["sid"])
                user = user or User.objects.filter(pk=access["user_id"]).first()
            except (TokenError, KeyError):
                pass

        expires_at = timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
        for sid in sids:
            try:
                RevokedSession.objects.get_or_create(sid=sid, defaults={"expires_at": expires_at})
            except IntegrityError:
                pass  # concurrent logout already recorded it
        if user:
            log_event(request, AuditLog.Action.LOGOUT, user=user, status_code=204)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response