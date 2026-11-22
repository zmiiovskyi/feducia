import re

from django.core.cache import cache
from django.test import Client

from feducia_project.testing import PASSWORD, AppTestCase

from .models import User


class SignUpTests(AppTestCase):
    def sign_up(self, **data):
        cache.clear()
        fields = {"username": "newcomer", "email": "new@example.org", "password": PASSWORD, **data}
        return self.client_for().post("/signup/", fields)

    def test_valid_sign_up_logs_in(self):
        self.assertRedirects(self.sign_up(), "/dashboard/", fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="newcomer").exists())

    def test_invalid_data_is_rejected(self):
        cases = [
            {"password": "1"},
            {"password": "password"},
            {"password": "12345678"},
            {"username": "<img src=x>"},
            {"username": "x" * 200},
            {"email": "not-an-email"},
            {"email": "OWNER@example.com"},
            {"username": ""},
        ]
        for data in cases:
            with self.subTest(data=data):
                self.assertEqual(self.sign_up(**data).status_code, 200)
                self.assertEqual(User.objects.count(), 1)

    def test_error_is_shown_and_fields_are_kept(self):
        response = self.sign_up(password="1")
        self.assertContains(response, "too short")
        self.assertContains(response, 'value="newcomer"')
        self.assertContains(response, 'value="new@example.org"')

    def test_empty_post(self):
        self.assertContains(self.client_for().post("/signup/"), "All fields are required.")


class LoginTests(AppTestCase):
    def test_login(self):
        response = self.client_for().post("/login/", {"username": "owner", "password": PASSWORD})
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    def test_error_is_shown_and_username_is_kept(self):
        response = self.client_for().post("/login/", {"username": "owner", "password": "wrong"})
        self.assertContains(response, "Incorrect username or password.")
        self.assertContains(response, 'value="owner"')

    def test_google_login_requires_post(self):
        self.assertEqual(self.client_for().get("/accounts/google/login/").status_code, 200)

    def test_google_button_works_with_csrf(self):
        for page in ("/login/", "/signup/"):
            with self.subTest(page=page):
                client = Client(enforce_csrf_checks=True)
                html = client.get(page).content.decode()
                match = re.search(r'action="(/accounts/google/login/)".*?value="([^"]+)"', html, re.S)
                response = client.post(match[1], {"csrfmiddlewaretoken": match[2]})
                self.assertIn("accounts.google.com", response["Location"])


class RateLimitTests(AppTestCase):
    def test_forms_are_rate_limited(self):
        limits = {
            "/login/": 10,
            "/signup/": 10,
            "/admin/login/": 10,
            "/password-reset/": 5,
            "/contacts/": 5,
            "/save-recording/": 20,
        }
        for path, limit in limits.items():
            with self.subTest(path=path):
                cache.clear()
                client = self.client_for(self.user if path == "/save-recording/" else None)
                codes = [client.post(path).status_code for _ in range(limit + 1)]
                self.assertNotIn(429, codes[:-1])
                self.assertEqual(codes[-1], 429)
