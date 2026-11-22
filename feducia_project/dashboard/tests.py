import os
import re
from unittest import mock

from django.core import mail
from django.test import Client

from feducia_project.testing import PASSWORD, AppTestCase, image_bytes

from .models import Profile


class PageTests(AppTestCase):
    def test_pages_render(self):
        pages = [
            "/", "/about/", "/contacts/", "/privacy/", "/terms/", "/login/", "/signup/",
            "/password-reset/", "/dashboard/", "/profile/", "/change-profile/",
            "/change-password/", "/recording/",
        ] + [f"/guide/{number}/" for number in range(1, 12)]

        for page in pages:
            with self.subTest(page=page):
                self.assertEqual(self.client.get(page).status_code, 200)

    def test_private_pages_require_login(self):
        for page in ("/dashboard/", "/profile/", "/change-profile/", "/recording/"):
            with self.subTest(page=page):
                self.assertEqual(self.client_for().get(page).status_code, 302)


class AccountTests(AppTestCase):
    def test_get_does_not_log_out_or_delete(self):
        for path in ("/logout/", "/delete-account/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)
                self.assertIn("_auth_user_id", self.client.session)

    def test_allauth_logout_requires_post(self):
        self.client.get("/accounts/logout/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_without_csrf_is_refused(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/delete-account/").status_code, 403)

    def test_profile_buttons_work_with_csrf(self):
        for path in ("/logout/", "/delete-account/"):
            with self.subTest(path=path):
                client = Client(enforce_csrf_checks=True)
                client.force_login(self.user)
                html = client.get("/profile/").content.decode()
                token = re.search(f'action="{path}".*?value="([^"]+)"', html, re.S)[1]
                self.assertEqual(client.post(path, {"csrfmiddlewaretoken": token}).status_code, 302)

    def test_email_of_another_user_is_refused(self):
        self.create_user("other")
        self.client.post("/change-profile/", {"username": "owner", "email": "OTHER@example.com"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "owner@example.com")

    def test_profile_update_shows_message(self):
        response = self.client.post(
            "/change-profile/", {"username": "owner", "email": "owner@example.com"}, follow=True
        )
        self.assertContains(response, "Profile updated!")


class AvatarTests(AppTestCase):
    def test_image_formats(self):
        for image_format, name in (("PNG", "a.png"), ("JPEG", "a.JPG"), ("GIF", "a.gif"), ("WEBP", "a.webp")):
            with self.subTest(image_format=image_format):
                content = image_bytes(image_format)
                url = self.upload_avatar(name, content).json()["avatar_url"]
                self.assertEqual(b"".join(self.client.get(url).streaming_content), content)

    def test_bad_files_are_rejected(self):
        files = {
            "x.html": b"<script>alert(1)</script>",
            "x.svg": b"<svg/>",
            "x.png": b"<script>alert(1)</script>",
            "polyglot.html": image_bytes(),
            "large.png": image_bytes() + b"0" * (5 * 1024 * 1024),
        }
        for name, content in files.items():
            with self.subTest(name=name):
                self.assertEqual(self.upload_avatar(name, content).status_code, 400)

    def test_avatar_is_shown_after_reload(self):
        url = self.upload_avatar().json()["avatar_url"]
        for page in ("/profile/", "/change-profile/"):
            with self.subTest(page=page):
                self.assertContains(self.client.get(page), url)

    def test_avatar_is_private(self):
        url = self.upload_avatar().json()["avatar_url"]
        self.assertEqual(self.client_for(self.create_user("other")).get(url).status_code, 404)

    def test_old_file_is_removed_on_replace(self):
        self.upload_avatar()
        old_path = Profile.objects.get(user=self.user).avatar.path
        self.upload_avatar()
        self.assertFalse(os.path.exists(old_path))

    def test_file_is_removed_with_account(self):
        self.upload_avatar()
        path = Profile.objects.get(user=self.user).avatar.path
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/delete-account/")
        self.assertFalse(os.path.exists(path))


class PasswordResetTests(AppTestCase):
    def request_link(self):
        self.client_for().post("/password-reset/", {"email": "OWNER@example.com"})
        return re.search(r"http://testserver(\S+)", mail.outbox[-1].body)[1]

    def test_reset_works_once(self):
        link = self.request_link()
        password = PASSWORD + "-new"
        response = self.client_for().post(
            link, {"password": password, "confirm_password": password}, follow=True
        )
        self.assertContains(response, "Password updated!")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(password))
        self.assertContains(self.client_for().get(link), "Invalid link.")

    def test_common_password_is_refused(self):
        self.client_for().post(self.request_link(), {"password": "password", "confirm_password": "password"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_response_does_not_reveal_accounts(self):
        known = self.client_for().post("/password-reset/", {"email": self.user.email})
        unknown = self.client_for().post("/password-reset/", {"email": "nobody@example.com"})
        self.assertEqual(known.context["message"], unknown.context["message"])

    def test_smtp_error_is_hidden(self):
        error = RuntimeError("smtp-internal-host")
        with mock.patch("dashboard.views.EmailMultiAlternatives.send", side_effect=error):
            with self.assertLogs("dashboard.views", "ERROR"):
                response = self.client_for().post("/password-reset/", {"email": self.user.email})
        self.assertNotContains(response, "smtp-internal-host")


class ContactTests(AppTestCase):
    data = {"name": "Ann\r\nBcc: x@evil.test", "email": "ann@example.com", "message": "Hello"}

    def test_message_is_sent_and_confirmed(self):
        response = self.client.post("/contacts/", self.data, follow=True)
        self.assertContains(response, "Message successfully sent!")
        self.assertNotIn("\n", mail.outbox[0].subject)

    def test_mail_error_is_shown_without_details(self):
        with mock.patch("dashboard.views.send_mail", side_effect=RuntimeError("smtp-internal-host")):
            with self.assertLogs("dashboard.views", "ERROR"):
                response = self.client.post("/contacts/", self.data)
        self.assertContains(response, "Could not send the message.")
        self.assertNotContains(response, "smtp-internal-host")
