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
