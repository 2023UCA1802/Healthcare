from django.conf import settings
from django.contrib.auth import get_user_model

from audit.models import AuditLog
from core.testing import PASSWORD, BaseAPITestCase
from rest_framework.test import APIClient

User = get_user_model()
COOKIE = settings.REFRESH_COOKIE_NAME
ORIGIN = settings.TRUSTED_ORIGINS[0]


class RegisterTests(BaseAPITestCase):
    url = "/api/auth/register/"

    def test_register_creates_user_with_lowercased_email(self):
        res = self.client.post(self.url, {"name": "Asha", "email": "Asha@Example.com", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.filter(email="asha@example.com").exists())
        self.assertNotIn("user", res.json())  # nothing about the account is echoed back
        self.assertTrue(AuditLog.objects.filter(action="REGISTER").exists())

    def test_duplicate_email_gets_identical_response_and_no_second_user(self):
        payload = {"name": "Asha", "email": "asha@example.com", "password": PASSWORD}
        first = self.client.post(self.url, payload, format="json")
        again = self.client.post(self.url, {**payload, "email": "ASHA@example.com", "name": "Other"}, format="json")
        self.assertEqual((first.status_code, first.json()), (again.status_code, again.json()))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().name, "Asha")  # existing account untouched

    def test_weak_password_rejected(self):
        res = self.client.post(self.url, {"name": "A", "email": "a@example.com", "password": "password"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.json())

    def test_register_is_rate_limited(self):
        codes = [
            self.client.post(self.url, {"name": "A", "email": f"u{i}@example.com", "password": PASSWORD}, format="json").status_code
            for i in range(6)
        ]
        self.assertEqual(codes[:5], [201] * 5)
        self.assertEqual(codes[5], 429)


class LoginTests(BaseAPITestCase):
    url = "/api/auth/login/"

    def setUp(self):
        super().setUp()
        self.user = self.make_user()

    def login(self, password=PASSWORD, email="asha@example.com", client=None):
        return (client or self.client).post(self.url, {"email": email, "password": password}, format="json")

    def test_success_returns_access_in_body_and_refresh_only_in_httponly_cookie(self):
        res = self.login(email="ASHA@example.com")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertEqual(body["user"]["email"], "asha@example.com")
        cookie = res.cookies[COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], settings.REFRESH_COOKIE_SAMESITE)
        self.assertEqual(cookie["path"], "/api/auth/")

    def test_access_token_works_on_protected_endpoint(self):
        access = self.login().json()["access"]
        res = self.client.get("/api/patients/", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.get("/api/patients/").status_code, 401)

    def test_wrong_password_and_unknown_email_look_identical(self):
        bad_pw = self.login(password="wrong-password")
        unknown = self.login(email="nobody@example.com")
        self.assertEqual(bad_pw.status_code, 400)
        self.assertEqual(bad_pw.json(), unknown.json())
        self.assertEqual(AuditLog.objects.filter(action="LOGIN_FAILED").count(), 2)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 400)

    def test_per_email_throttle_locks_after_five_attempts(self):
        codes = [self.login(password=f"wrong-{i}").status_code for i in range(6)]
        self.assertEqual(codes, [400] * 5 + [429])
        self.assertEqual(self.login().status_code, 429)  # even the right password is blocked now

    def test_per_ip_throttle_not_bypassable_with_spoofed_forwarded_header(self):
        codes = []
        for i in range(11):
            res = self.client.post(
                self.url, {"email": f"user{i}@example.com", "password": "x"}, format="json",
                HTTP_X_FORWARDED_FOR=f"10.0.0.{i}",
            )
            codes.append(res.status_code)
        self.assertEqual(codes[-1], 429)


class RefreshAndLogoutTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()
        self.client = APIClient()
        res = self.client.post("/api/auth/login/", {"email": "asha@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)

    def refresh(self, client=None, **extra):
        return (client or self.client).post("/api/auth/token/refresh/", HTTP_ORIGIN=ORIGIN, **extra)

    def test_refresh_returns_new_access_user_and_rotates_cookie(self):
        old = self.client.cookies[COOKIE].value
        res = self.refresh()
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())
        self.assertEqual(res.json()["user"]["email"], "asha@example.com")
        self.assertNotEqual(self.client.cookies[COOKIE].value, old)

    def test_old_refresh_token_cannot_be_reused_after_rotation(self):
        old = self.client.cookies[COOKIE].value
        self.assertEqual(self.refresh().status_code, 200)
        thief = APIClient()
        thief.cookies[COOKIE] = old
        self.assertEqual(self.refresh(thief).status_code, 401)

    def test_refresh_without_cookie_is_401(self):
        self.assertEqual(self.refresh(APIClient()).status_code, 401)

    def test_refresh_from_untrusted_origin_is_rejected(self):
        res = self.client.post("/api/auth/token/refresh/", HTTP_ORIGIN="https://evil.example")
        self.assertEqual(res.status_code, 403)

    def test_refresh_fails_for_deactivated_user(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.refresh().status_code, 401)

    def test_logout_revokes_refresh_token_server_side(self):
        stolen = self.client.cookies[COOKIE].value
        res = self.client.post("/api/auth/logout/", HTTP_ORIGIN=ORIGIN)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.cookies[COOKIE].value, "")  # cookie cleared
        attacker = APIClient()
        attacker.cookies[COOKIE] = stolen
        self.assertEqual(self.refresh(attacker).status_code, 401)  # stolen token is dead
        self.assertTrue(AuditLog.objects.filter(action="LOGOUT").exists())

    def test_logout_without_session_is_still_204(self):
        self.assertEqual(APIClient().post("/api/auth/logout/", HTTP_ORIGIN=ORIGIN).status_code, 204)

    def test_logout_from_untrusted_origin_is_rejected(self):
        self.assertEqual(self.client.post("/api/auth/logout/", HTTP_ORIGIN="https://evil.example").status_code, 403)


class AccessTokenRevocationTests(BaseAPITestCase):
    """Logging out must kill the session's access tokens immediately."""

    def setUp(self):
        super().setUp()
        self.user = self.make_user()

    def login(self):
        client = APIClient()
        res = client.post("/api/auth/login/", {"email": "asha@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        return client, res.json()["access"]

    @staticmethod
    def get_patients(access):
        return APIClient().get("/api/patients/", HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_access_token_stops_working_immediately_after_logout(self):
        client, access = self.login()
        self.assertEqual(self.get_patients(access).status_code, 200)
        self.assertEqual(client.post("/api/auth/logout/", HTTP_ORIGIN=ORIGIN).status_code, 204)
        res = self.get_patients(access)
        self.assertEqual(res.status_code, 401)
        self.assertIn("revoked", str(res.json()).lower())

    def test_logout_only_ends_that_session_other_devices_keep_working(self):
        phone, phone_access = self.login()
        _laptop, laptop_access = self.login()
        phone.post("/api/auth/logout/", HTTP_ORIGIN=ORIGIN)
        self.assertEqual(self.get_patients(phone_access).status_code, 401)
        self.assertEqual(self.get_patients(laptop_access).status_code, 200)

    def test_all_tokens_of_the_session_die_including_ones_issued_by_refresh(self):
        client, first_access = self.login()
        second_access = client.post("/api/auth/token/refresh/", HTTP_ORIGIN=ORIGIN).json()["access"]
        self.assertEqual(self.get_patients(first_access).status_code, 200)  # still same live session
        self.assertEqual(self.get_patients(second_access).status_code, 200)
        client.post("/api/auth/logout/", HTTP_ORIGIN=ORIGIN)
        self.assertEqual(self.get_patients(first_access).status_code, 401)
        self.assertEqual(self.get_patients(second_access).status_code, 401)

    def test_logout_with_only_a_bearer_token_and_no_cookie_still_revokes(self):
        _client, access = self.login()
        res = APIClient().post("/api/auth/logout/", HTTP_AUTHORIZATION=f"Bearer {access}", HTTP_ORIGIN=ORIGIN)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self.get_patients(access).status_code, 401)

    def test_logging_in_again_after_logout_gives_a_working_new_session(self):
        client, old_access = self.login()
        client.post("/api/auth/logout/", HTTP_ORIGIN=ORIGIN)
        _client2, new_access = self.login()
        self.assertEqual(self.get_patients(old_access).status_code, 401)
        self.assertEqual(self.get_patients(new_access).status_code, 200)

    def test_cannot_refresh_a_revoked_session(self):
        from accounts.models import RevokedSession
        client, _access = self.login()
        # revoke the session without going through logout (e.g. admin action)
        from rest_framework_simplejwt.tokens import RefreshToken
        sid = RefreshToken(client.cookies[COOKIE].value)["sid"]
        from django.utils import timezone
        RevokedSession.objects.create(sid=sid, expires_at=timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
        self.assertEqual(client.post("/api/auth/token/refresh/", HTTP_ORIGIN=ORIGIN).status_code, 401)

    def test_token_without_a_session_id_is_rejected(self):
        from rest_framework_simplejwt.tokens import AccessToken
        legacy = str(AccessToken.for_user(self.user))  # no `sid` claim
        self.assertEqual(self.get_patients(legacy).status_code, 401)

    def test_deactivated_user_token_is_rejected(self):
        _client, access = self.login()
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.get_patients(access).status_code, 401)

    def test_purge_command_removes_only_expired_rows(self):
        from datetime import timedelta
        from io import StringIO

        from django.core.management import call_command
        from django.utils import timezone

        from accounts.models import RevokedSession
        RevokedSession.objects.create(sid="a" * 32, expires_at=timezone.now() - timedelta(days=1))
        RevokedSession.objects.create(sid="b" * 32, expires_at=timezone.now() + timedelta(days=1))
        out = StringIO()
        call_command("flushrevokedsessions", stdout=out)
        self.assertEqual(list(RevokedSession.objects.values_list("sid", flat=True)), ["b" * 32])